"""Fase 3 pelo terminal: executa as consultas de consulta.sql no Oracle da FIAP e imprime as tabelas.

Criado na Fase 7 para o main.py da raiz e a dashboard dispararem a Fase 3 sem o SQL Developer.
Roda com o ambiente da dashboard da Fase 3 (oracledb + python-dotenv):

    uv run --project fase3/dashboard python fase3/consultas.py            # a partir da raiz
    uv run --project fase3/dashboard python fase3/consultas.py --json     # saída para outro programa

As credenciais vêm do .env único da raiz (ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN).
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import oracledb
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent


def ler_consultas(arquivo: Path) -> list[str]:
    """Separa o arquivo .sql em comandos (um por `;`), ignorando comentários `--`."""
    linhas = [l for l in arquivo.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")]
    return [c.strip() for c in "\n".join(linhas).split(";") if c.strip()]


def conectar():
    load_dotenv()  # sobe as pastas até achar o .env da raiz
    user, password, dsn = (os.getenv(k) for k in ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"))
    if not all((user, password, dsn)):
        sys.exit("Defina ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN no .env da raiz (veja .env.example).")
    try:
        return oracledb.connect(user=user, password=password, dsn=dsn)
    except oracledb.Error as e:
        sys.exit(f"Não foi possível conectar ao Oracle ({dsn}): {e}")


def valor(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def tabela(colunas: list[str], linhas: list[tuple]) -> str:
    celulas = [[("" if v is None else str(valor(v))) for v in linha] for linha in linhas]
    larguras = [max(len(c), *(len(l[i]) for l in celulas)) if celulas else len(c) for i, c in enumerate(colunas)]
    fmt = lambda vals: " | ".join(v.ljust(w) for v, w in zip(vals, larguras))
    saida = [fmt(colunas), "-+-".join("-" * w for w in larguras), *(fmt(l) for l in celulas)]
    return "\n".join(saida)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Executa as consultas da Fase 3 no Oracle.")
    p.add_argument("--sql", type=Path, default=AQUI / "consulta.sql", help="arquivo .sql (padrão: consulta.sql)")
    p.add_argument("--json", action="store_true", help="imprime os resultados em JSON")
    args = p.parse_args(argv)

    consultas = ler_consultas(args.sql)
    resultados = []
    with conectar() as conn, conn.cursor() as cur:
        for sql in consultas:
            cur.execute(sql)
            colunas = [d[0] for d in cur.description]
            linhas = cur.fetchall()
            resultados.append({"sql": sql, "colunas": colunas, "linhas": [[valor(v) for v in l] for l in linhas]})

    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
        return 0
    for i, r in enumerate(resultados, 1):
        print(f"\n== Consulta {i}: {' '.join(r['sql'].split())}")
        print(tabela(r["colunas"], r["linhas"]) if r["linhas"] else "(sem linhas)")
        print(f"({len(r['linhas'])} linha{'s' if len(r['linhas']) != 1 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
