#!/usr/bin/env python3
"""Descobre por que o equipamento não aparece conectado na tela.

O sintoma clássico: a API está saudável, o ESP32 está rodando, e o painel insiste em
"offline". Quase sempre é a mesma causa — **a API e o dispositivo estão em brokers
diferentes** — e nada na tela diz isso, porque cada lado funciona perfeitamente no seu
canto.

Este script pergunta as quatro coisas que resolvem o caso:

1. em qual broker a **API** está ouvindo;
2. se há tráfego de dispositivo no broker **local** (o do docker-compose);
3. se há tráfego de dispositivo no broker **público** (o padrão do firmware);
4. se o prefixo dos tópicos é o mesmo nas duas pontas.

Uso:
    uv run --project api python scripts/diagnosticar_mqtt.py
    uv run --project api python scripts/diagnosticar_mqtt.py --segundos 20
"""

from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.request

from _bootstrap import bootstrap

ROOT = bootstrap()

import paho.mqtt.client as mqtt

API_URL = "http://localhost:8000"
BROKER_LOCAL = "127.0.0.1"
BROKER_PUBLICO = "broker.hivemq.com"
PREFIXO_PADRAO = "agrishield/fiap-sompo-2026"

#: Sufixos que **o dispositivo** publica. O `config` é publicado pela API, então
#: encontrá-lo sozinho não prova que há equipamento vivo — é o engano mais comum.
SUFIXOS_DO_DISPOSITIVO = ("telemetry", "events", "status")


def api_esta_no_ar() -> dict | None:
    try:
        with urllib.request.urlopen(f"{API_URL}/api/v1/health", timeout=5) as resposta:
            return json.load(resposta)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def estado_do_dispositivo(device_id: str) -> dict | None:
    try:
        with urllib.request.urlopen(
            f"{API_URL}/api/v1/devices/{device_id}/status", timeout=5
        ) as resposta:
            return json.load(resposta)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def escuta(host: str, prefixo: str, segundos: int) -> tuple[list[str], str | None]:
    """Assina `prefixo/#` e devolve (tópicos vistos, erro)."""
    vistos: list[str] = []
    cliente = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id=f"diag-{int(time.time())}"
    )
    cliente.on_message = lambda _c, _u, mensagem: vistos.append(mensagem.topic)
    try:
        cliente.connect(host, 1883, 15)
    except (TimeoutError, OSError) as erro:
        return [], f"não deu para conectar: {erro}"
    cliente.subscribe(f"{prefixo}/#", qos=1)
    cliente.loop_start()
    time.sleep(segundos)
    cliente.loop_stop()
    cliente.disconnect()
    return vistos, None


def separa(topicos: list[str]) -> tuple[set[str], set[str]]:
    """Divide entre o que o **dispositivo** publica e o resto (a API publica `config`)."""
    do_dispositivo = {
        t for t in topicos if t.rsplit("/", 1)[-1] in SUFIXOS_DO_DISPOSITIVO
    }
    outros = set(topicos) - do_dispositivo
    return do_dispositivo, outros


def ips_da_maquina() -> list[str]:
    """IPs que o ESP32 usaria para falar com o broker local (nunca `localhost`)."""
    encontrados = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith(("127.", "172.17.", "172.18.", "172.19.")):
                encontrados.append(ip)
    except socket.gaierror:
        pass
    return sorted(set(encontrados))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--segundos", type=int, default=12, help="quanto escutar cada broker"
    )
    parser.add_argument("--prefixo", default=PREFIXO_PADRAO)
    parser.add_argument("--dispositivo", default="tractor-01")
    args = parser.parse_args(argv)

    print("=" * 78)
    print("Diagnóstico MQTT do AgriShield")
    print("=" * 78)

    # 1. A API
    saude = api_esta_no_ar()
    if saude is None:
        print("\n[1] API .......... NÃO responde em", API_URL)
        print("    Suba com `docker compose up -d` ou `./scripts/run-demo.sh`.")
        return 1
    print(f"\n[1] API .......... no ar (ambiente `{saude.get('environment')}`)")

    estado = estado_do_dispositivo(args.dispositivo)
    if estado:
        visto = estado.get("last_seen_at") or "nunca"
        print(
            f"    `{args.dispositivo}`: estado **{estado.get('state')}**, última leitura: {visto}"
        )
        if estado.get("reported_state") is None:
            print(
                "    ⚠️  `reported_state` é nulo: a API **nunca** recebeu nada deste equipamento."
            )

    # 2 e 3. Os dois brokers
    resultados: dict[str, tuple[set[str], set[str], str | None]] = {}
    for rotulo, host in (
        ("local (docker-compose)", BROKER_LOCAL),
        ("público", BROKER_PUBLICO),
    ):
        print(
            f"\n[{2 if host == BROKER_LOCAL else 3}] Escutando o broker {rotulo} por"
            f" {args.segundos}s..."
        )
        topicos, erro = escuta(host, args.prefixo, args.segundos)
        if erro:
            print(f"    {erro}")
            resultados[host] = (set(), set(), erro)
            continue
        do_disp, outros = separa(topicos)
        resultados[host] = (do_disp, outros, None)
        if do_disp:
            print(f"    ✓ equipamento publicando: {sorted(do_disp)}")
        else:
            print("    — nenhum tráfego de equipamento")
        if outros:
            print(f"    (também vi, publicado pela API: {sorted(outros)})")

    # 4. Veredito
    print("\n" + "=" * 78)
    local_tem = bool(resultados[BROKER_LOCAL][0])
    publico_tem = bool(resultados[BROKER_PUBLICO][0])

    if local_tem and publico_tem:
        print(
            "VEREDITO: há equipamento nos **dois** brokers. Provavelmente duas simulações"
        )
        print("abertas. Feche uma — telemetria duplicada confunde o painel.")
    elif not local_tem and not publico_tem:
        print("VEREDITO: **nenhum equipamento publicando** em nenhum dos dois brokers.")
        print("O ESP32 não está rodando, não conectou no Wi-Fi, ou usa outro prefixo.")
        print("Olhe o Serial do Wokwi: deve aparecer `[mqtt] conectando em ...`.")
    else:
        onde = "público" if publico_tem else "local"
        outro = "local" if publico_tem else "público"
        print(f"VEREDITO: o equipamento está publicando no broker **{onde}**.")
        print("Agora confira se a API está ouvindo o MESMO broker:")
        print("    docker compose exec api printenv AGRISHIELD_MQTT_HOST")
        print(f"Se ela estiver no **{outro}**, é esta a causa do 'offline' na tela.")
        if publico_tem:
            print("\nCorreção — no `.env` da raiz:")
            print("    AGRISHIELD_MQTT_HOST=broker.hivemq.com")
        else:
            print("\nCorreção — no `.env` da raiz:")
            print("    AGRISHIELD_MQTT_HOST=mosquitto")
        print("Depois: `docker compose up -d api`")

    ips = ips_da_maquina()
    if ips:
        print(
            f"\nPara apontar o firmware ao broker local, use o IP da LAN: {', '.join(ips)}"
        )
        print("    (nunca `localhost`: para o ESP32 simulado, `localhost` é ele mesmo)")
        print(
            f"    PLATFORMIO_BUILD_FLAGS='-D AGRISHIELD_MQTT_HOST=\\\"{ips[0]}\\\"' pio run"
        )
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
