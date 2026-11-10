"""Ponte entre a dashboard e o `main.py` da raiz: roda serviços e mantém os que ficam no ar.

Toda a lógica de "como disparar cada fase" fica no main.py; aqui só chamamos
`python3 main.py <serviço> [args]` e devolvemos a saída para a tela.
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parents[3]          # fase4/src/core/ -> raiz do repositório
MAIN = RAIZ / "main.py"
IMAGENS = RAIZ / "docs" / "imagens"
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
URL_DASH_FASE3 = "http://localhost:8502"

PORTAS = {"fase4-api": 8000, "fase3-dashboard": 8502}


@dataclass
class Resultado:
    codigo: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.codigo in (0, 2)  # 2 = Fase 6 sem detecções

    def json(self):
        return json.loads(self.stdout)


def rodar(servico: str, *args: str, timeout: int = 300) -> Resultado:
    """Roda `main.py <servico> args...` até terminar e devolve stdout/stderr."""
    cmd = [sys.executable, str(MAIN), servico, *map(str, args)]
    try:
        p = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Resultado(124, "", f"{servico} passou de {timeout}s e foi interrompido.")
    return Resultado(p.returncode, p.stdout, p.stderr)


@st.cache_resource
def _processos() -> dict[str, subprocess.Popen]:
    """Serviços em segundo plano (API, dashboard da Fase 3); um só dicionário para todo o servidor."""
    atexit.register(_parar_todos)  # ao fechar a dashboard (Ctrl+C), os serviços iniciados por ela param junto
    return {}


def _parar_todos() -> None:
    for servico in list(_processos()):
        parar(servico)


def no_ar(servico: str) -> bool:
    p = _processos().get(servico)
    return p is not None and p.poll() is None


def iniciar(servico: str, *args: str) -> None:
    if no_ar(servico):
        return
    log = open(RAIZ / f".{servico}.log", "w")  # ignorado pelo git (.*.log na raiz)
    p = subprocess.Popen([sys.executable, str(MAIN), servico, *args], cwd=RAIZ, stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True)  # grupo próprio: dá para parar uv + uvicorn/streamlit de uma vez
    _processos()[servico] = p


def parar(servico: str) -> None:
    p = _processos().pop(servico, None)
    if p is None or p.poll() is not None:
        return
    try:
        os.killpg(p.pid, signal.SIGINT)
        p.wait(timeout=15)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def log_de(servico: str, linhas: int = 30) -> str:
    arq = RAIZ / f".{servico}.log"
    if not arq.exists():
        return ""
    return "\n".join(arq.read_text(errors="replace").splitlines()[-linhas:])


def porta_aberta(host: str, porta: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except OSError:
        return False


def api_responde() -> bool:
    try:
        return requests.get(f"{API_URL}/docs", timeout=3).ok
    except requests.RequestException:
        return False


def oracle_acessivel() -> bool:
    dsn = os.getenv("ORACLE_DSN", "")
    host, _, resto = dsn.partition(":")
    porta = int(resto.split("/")[0]) if resto else 1521
    return bool(host) and porta_aberta(host, porta)


def env_configurado() -> bool:
    return (RAIZ / ".env").exists() and bool(os.getenv("ORACLE_USER")) and os.getenv("ORACLE_USER") != "RM000000"


def aws_configurada() -> bool:
    return bool(os.getenv("SNS_TOPIC_ARN"))


def porta_da_api() -> int:
    return urlparse(API_URL).port or 8000


def mostrar_erro(r: Resultado, titulo: str = "O serviço terminou com erro") -> None:
    st.error(f"{titulo} (código {r.codigo}).")
    with st.expander("Detalhes"):
        st.code((r.stderr or r.stdout).strip()[-4000:] or "(sem saída)")
