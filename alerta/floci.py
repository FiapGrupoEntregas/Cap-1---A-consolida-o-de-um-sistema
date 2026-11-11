"""Prepara e inspeciona o SNS do floci (AWS local) para desenvolver o serviço de alerta.

    python3 main.py alerta-floci preparar   # cria o tópico farmtech-alertas, uma fila SQS assinante e um e-mail
    python3 main.py alerta-floci ler        # mostra as mensagens que chegaram na fila (prova de entrega)
    python3 main.py alerta-floci limpar     # remove tópico e fila

O floci não envia e-mail de verdade; a fila SQS assinada no tópico é a forma de ver que a
publicação funcionou. Na AWS real o mesmo tópico recebe uma assinatura de e-mail (ver o passo a
passo em docs/plano-entrega/04-alerta-aws.md).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
TOPICO = "farmtech-alertas"
FILA = "farmtech-alertas-fila"
EMAIL_EXEMPLO = "funcionarios@farmtech.exemplo"


def clientes():
    load_dotenv(AQUI.parent / ".env")
    endpoint = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    regiao = os.getenv("AWS_REGION", "us-east-1")
    kw = dict(region_name=regiao, endpoint_url=endpoint)
    return boto3.client("sns", **kw), boto3.client("sqs", **kw), endpoint


def preparar() -> int:
    sns, sqs, endpoint = clientes()
    topico = sns.create_topic(Name=TOPICO)["TopicArn"]
    fila_url = sqs.create_queue(QueueName=FILA)["QueueUrl"]
    fila_arn = sqs.get_queue_attributes(QueueUrl=fila_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    assinaturas = sns.list_subscriptions_by_topic(TopicArn=topico)["Subscriptions"]
    if not any(s["Endpoint"] == fila_arn for s in assinaturas):
        sns.subscribe(TopicArn=topico, Protocol="sqs", Endpoint=fila_arn)
    if not any(s["Protocol"] == "email" for s in assinaturas):
        sns.subscribe(TopicArn=topico, Protocol="email", Endpoint=EMAIL_EXEMPLO)
    print(json.dumps({"endpoint": endpoint, "topico": topico, "fila": fila_url,
                      "assinaturas": [(s["Protocol"], s["Endpoint"]) for s in sns.list_subscriptions_by_topic(TopicArn=topico)["Subscriptions"]],
                      "proximo_passo": f"coloque no .env: SNS_TOPIC_ARN={topico}"}, indent=2, ensure_ascii=False))
    return 0


def ler(apagar: bool) -> int:
    sns, sqs, endpoint = clientes()
    fila_url = sqs.get_queue_url(QueueName=FILA)["QueueUrl"]
    mensagens = []
    while True:
        lote = sqs.receive_message(QueueUrl=fila_url, MaxNumberOfMessages=10, WaitTimeSeconds=1).get("Messages", [])
        if not lote:
            break
        for m in lote:
            corpo = json.loads(m["Body"])  # envelope do SNS: Subject, Message, Timestamp, MessageId...
            mensagens.append({"MessageId": corpo.get("MessageId"), "Timestamp": corpo.get("Timestamp"),
                              "Subject": corpo.get("Subject"), "Message": corpo.get("Message")})
            if apagar:
                sqs.delete_message(QueueUrl=fila_url, ReceiptHandle=m["ReceiptHandle"])
    print(json.dumps({"endpoint": endpoint, "fila": fila_url, "total": len(mensagens), "mensagens": mensagens},
                     indent=2, ensure_ascii=False))
    return 0


def limpar() -> int:
    sns, sqs, _ = clientes()
    for t in sns.list_topics()["Topics"]:
        if t["TopicArn"].endswith(f":{TOPICO}"):
            sns.delete_topic(TopicArn=t["TopicArn"])
    try:
        sqs.delete_queue(QueueUrl=sqs.get_queue_url(QueueName=FILA)["QueueUrl"])
    except sqs.exceptions.QueueDoesNotExist:
        pass
    print("tópico e fila removidos do floci")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="SNS/SQS do floci para o serviço de alerta.")
    p.add_argument("acao", choices=["preparar", "ler", "limpar"])
    p.add_argument("--manter", action="store_true", help="em `ler`, não apaga as mensagens da fila")
    args = p.parse_args(argv)
    try:
        return {"preparar": preparar, "ler": lambda: ler(apagar=not args.manter), "limpar": limpar}[args.acao]()
    except Exception as e:
        sys.exit(f"Erro falando com o floci: {e}\nEle está no ar? `docker compose up -d` na raiz.")


if __name__ == "__main__":
    sys.exit(main())
