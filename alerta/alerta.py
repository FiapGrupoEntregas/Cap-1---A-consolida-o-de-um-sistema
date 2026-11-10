"""Serviço de alerta da FarmTech (Fase 7): avalia as leituras dos sensores e publica no Amazon SNS.

    python3 main.py alerta                       # última leitura de SOIL_DATA (Oracle) → regras → SNS
    python3 main.py alerta --ultimas 5           # avalia as 5 leituras mais recentes
    python3 main.py alerta --fonte api           # lê pela API da Fase 4 (GET /soil) em vez do Oracle
    python3 main.py alerta --simular seco        # leitura de exemplo (seco | acido | alcalino | npk | ok)
    python3 main.py alerta --yolo fase6/saidas/x.json   # inclui o resultado do detect.py (vaca → cercas)
    python3 main.py alerta --dry-run             # mostra o que seria publicado, sem publicar

Para onde vai: tópico SNS em SNS_TOPIC_ARN (.env). Com AWS_ENDPOINT_URL definido (ex.:
http://localhost:4566) o boto3 fala com o floci, o emulador local; sem ele, com a AWS real, usando as
credenciais padrão do boto3 (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY no .env ou ~/.aws/credentials).

Saída (stdout): um JSON com as leituras avaliadas, os alertas, o que foi publicado e o destino.
Códigos de saída: 0 sem alertas ou alertas publicados; 4 houve alertas mas a publicação falhou.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from regras import Alerta, avaliar_deteccao, avaliar_leitura, montar_mensagem

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / ".estado.json"  # último envio de cada condição (ignorado pelo git)
CAMPOS = ["id", "soil_moisture_percent", "ph", "nitrogen", "phosphorus", "potassium", "air_temperature",
          "air_humidity", "light_percent", "created_at"]

SIMULACOES = {
    "ok": {"soil_moisture_percent": 72, "ph": 6.4, "nitrogen": 55, "phosphorus": 48, "potassium": 61},
    "seco": {"soil_moisture_percent": 35, "ph": 6.3, "nitrogen": 55, "phosphorus": 48, "potassium": 61},
    "acido": {"soil_moisture_percent": 68, "ph": 5.2, "nitrogen": 55, "phosphorus": 48, "potassium": 61},
    "alcalino": {"soil_moisture_percent": 68, "ph": 7.4, "nitrogen": 55, "phosphorus": 48, "potassium": 61},
    "npk": {"soil_moisture_percent": 68, "ph": 6.3, "nitrogen": 12, "phosphorus": 20, "potassium": 65},
    "tudo": {"soil_moisture_percent": 22, "ph": 5.1, "nitrogen": 8, "phosphorus": 15, "potassium": 10},
}


def log(msg: str) -> None:
    print(f"[alerta] {msg}", file=sys.stderr, flush=True)


# ------------------------------------------------------------------ leituras
def ler_oracle(n: int) -> list[dict]:
    import oracledb

    user, password, dsn = (os.getenv(k) for k in ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"))
    if not all((user, password, dsn)):
        sys.exit("Defina ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN no .env da raiz.")
    sql = f"SELECT {', '.join(CAMPOS)} FROM soil_data ORDER BY id DESC FETCH FIRST :n ROWS ONLY"
    try:
        with oracledb.connect(user=user, password=password, dsn=dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, {"n": n})
            cols = [d[0].lower() for d in cur.description]
            return [dict(zip(cols, linha)) for linha in cur.fetchall()]
    except oracledb.Error as e:
        sys.exit(f"Não foi possível ler SOIL_DATA no Oracle: {e}")


def ler_api(n: int) -> list[dict]:
    import requests

    url = os.getenv("API_URL", "http://127.0.0.1:8000")
    try:
        r = requests.get(f"{url}/soil", params={"limit": n}, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        sys.exit(f"Não foi possível ler a API da Fase 4 em {url} (ela está no ar? `python3 main.py fase4-api`): {e}")


def ler_yolo(arquivo: Path) -> dict:
    try:
        return json.loads(arquivo.read_text())
    except (OSError, ValueError) as e:
        sys.exit(f"Não consegui ler o JSON do detect.py em {arquivo}: {e}")


# ------------------------------------------------------------------ não repetir
def carregar_estado() -> dict:
    try:
        return json.loads(ESTADO.read_text())
    except (OSError, ValueError):
        return {}


def filtrar_repetidos(alertas: list[Alerta], estado: dict, intervalo_min: int, agora: datetime) -> tuple[list[Alerta], list[Alerta]]:
    """Separa os alertas novos dos que já foram enviados há menos de `intervalo_min` minutos."""
    novos, repetidos = [], []
    for a in alertas:
        ultimo = estado.get(a.chave)
        if ultimo and datetime.fromisoformat(ultimo) > agora - timedelta(minutes=intervalo_min):
            repetidos.append(a)
        else:
            novos.append(a)
    return novos, repetidos


# ------------------------------------------------------------------ publicar
def cliente_sns():
    import boto3

    endpoint = os.getenv("AWS_ENDPOINT_URL")
    if endpoint:  # floci: qualquer credencial serve, mas o boto3 exige alguma
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    return boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1"), endpoint_url=endpoint)


def publicar(assunto: str, corpo: str) -> str:
    topico = os.getenv("SNS_TOPIC_ARN")
    if not topico:
        raise RuntimeError("SNS_TOPIC_ARN não definido no .env (no floci: `python3 main.py alerta-floci preparar`).")
    return cliente_sns().publish(TopicArn=topico, Subject=assunto, Message=corpo)["MessageId"]


# ------------------------------------------------------------------ programa
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Avalia leituras dos sensores e publica alertas no Amazon SNS.")
    fonte = p.add_mutually_exclusive_group()
    fonte.add_argument("--fonte", choices=["oracle", "api"], default="oracle", help="de onde vêm as leituras (padrão: oracle)")
    fonte.add_argument("--simular", choices=sorted(SIMULACOES), help="usa uma leitura de exemplo em vez de ler os sensores")
    fonte.add_argument("--leitura", type=json.loads, help='leitura em JSON, ex.: \'{"ph": 5.0, "soil_moisture_percent": 40}\'')
    p.add_argument("--ultimas", type=int, default=1, help="quantas leituras recentes avaliar (padrão 1)")
    p.add_argument("--yolo", type=Path, help="JSON gerado pelo detect.py da Fase 6, para a regra de animal na lavoura")
    p.add_argument("--intervalo-min", type=int, default=60, help="não repetir a mesma condição antes de N minutos (padrão 60)")
    p.add_argument("--forcar", action="store_true", help="publica mesmo que a condição tenha sido alertada há pouco")
    p.add_argument("--dry-run", action="store_true", help="avalia e monta a mensagem, mas não publica")
    args = p.parse_args(argv)

    load_dotenv(AQUI.parent / ".env")
    agora = datetime.now()

    if args.simular:
        leituras, origem = [{"id": "simulacao", **SIMULACOES[args.simular]}], f"simulação '{args.simular}'"
    elif args.leitura is not None:
        leituras, origem = [{"id": "manual", **args.leitura}], "leitura informada na linha de comando"
    elif args.fonte == "api":
        leituras, origem = ler_api(args.ultimas), "API da Fase 4 (GET /soil)"
    else:
        leituras, origem = ler_oracle(args.ultimas), "Oracle da FIAP (SOIL_DATA)"
    log(f"{len(leituras)} leitura(s) de: {origem}")

    avaliacoes, alertas_por_chave = [], {}
    for leitura in leituras:
        alertas = avaliar_leitura(leitura)
        avaliacoes.append({"leitura": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in leitura.items()},
                           "alertas": [a.dict() for a in alertas]})
        for a in alertas:
            alertas_por_chave.setdefault(a.chave, a)  # a leitura mais recente vem primeiro
    if args.yolo:
        resumo = ler_yolo(args.yolo).get("resumo", {})
        for a in avaliar_deteccao(resumo):
            alertas_por_chave.setdefault(a.chave, a)
        avaliacoes.append({"deteccao": resumo, "alertas": [a.dict() for a in avaliar_deteccao(resumo)]})

    alertas = list(alertas_por_chave.values())
    estado = carregar_estado()
    novos, repetidos = ([alertas, []] if args.forcar else filtrar_repetidos(alertas, estado, args.intervalo_min, agora))

    destino = os.getenv("AWS_ENDPOINT_URL") and f"floci ({os.getenv('AWS_ENDPOINT_URL')})" or f"Amazon SNS ({os.getenv('AWS_REGION', 'us-east-1')})"
    resultado = {"quando": agora.isoformat(timespec="seconds"), "origem": origem, "avaliacoes": avaliacoes,
                 "alertas": [a.dict() for a in alertas], "repetidos_nao_enviados": [a.chave for a in repetidos],
                 "destino": destino, "topico": os.getenv("SNS_TOPIC_ARN"), "publicado": None}
    codigo = 0

    if novos:
        leitura_ref = leituras[0] if leituras else {}
        assunto, corpo = montar_mensagem(leitura_ref, novos, origem, agora.strftime("%d/%m/%Y %H:%M"))
        resultado["mensagem"] = {"assunto": assunto, "corpo": corpo}
        if args.dry_run:
            log("dry-run: nada publicado")
            resultado["publicado"] = False
        else:
            try:
                resultado["message_id"] = publicar(assunto, corpo)
                resultado["publicado"] = True
                for a in novos:
                    estado[a.chave] = agora.isoformat()
                ESTADO.write_text(json.dumps(estado, indent=2))
                log(f"publicado em {destino}: {len(novos)} alerta(s), MessageId {resultado['message_id']}")
            except Exception as e:  # credenciais, rede, tópico inexistente...
                resultado["publicado"] = False
                resultado["erro"] = str(e)
                log(f"falha ao publicar: {e}")
                codigo = 4
    else:
        log("nenhum alerta novo" + (f" ({len(repetidos)} repetido(s) dentro do intervalo)" if repetidos else ""))
        resultado["publicado"] = False

    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
