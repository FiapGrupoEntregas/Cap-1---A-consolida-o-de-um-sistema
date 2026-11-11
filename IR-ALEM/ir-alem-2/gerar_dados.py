"""Gera o arquivo de entrada do Ir Além 2 a partir das leituras reais de SOIL_DATA (Fase 4).

Cada leitura vira um "talhão" com área sorteada (semente fixa). O notebook lê só o CSV gerado, então
o resultado é reprodutível sem acesso ao Oracle. Rodar uma vez, a partir desta pasta:

    uv run python gerar_dados.py            # 20 talhões -> dados/talhoes.csv
    uv run python gerar_dados.py --n 30
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import oracledb
import pandas as pd
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "dados" / "talhoes.csv"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=20, help="quantas leituras recentes viram talhões")
    p.add_argument("--semente", type=int, default=42)
    args = p.parse_args()

    load_dotenv(AQUI.parents[1] / ".env")  # .env único da raiz
    user, password, dsn = (os.getenv(k) for k in ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"))
    if not all((user, password, dsn)):
        sys.exit("Defina ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN no .env da raiz.")
    sql = ("SELECT id, soil_moisture_percent, ph, nitrogen, phosphorus, potassium, created_at "
           "FROM soil_data ORDER BY id DESC FETCH FIRST :n ROWS ONLY")
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        df = pd.read_sql(sql, conn, params={"n": args.n})
    df.columns = [c.lower() for c in df.columns]
    df = df.sort_values("id").reset_index(drop=True)

    rng = np.random.default_rng(args.semente)
    df.insert(0, "talhao", [f"T{i + 1:02d}" for i in range(len(df))])
    df["area_ha"] = np.round(rng.uniform(2.0, 12.0, len(df)), 1)
    df = df.rename(columns={"id": "leitura_id", "soil_moisture_percent": "umidade", "nitrogen": "n",
                            "phosphorus": "p", "potassium": "k"})
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    SAIDA.parent.mkdir(exist_ok=True)
    df.to_csv(SAIDA, index=False)
    print(f"{len(df)} talhões gravados em {SAIDA}")
    print(df.head())
    return 0


if __name__ == "__main__":
    sys.exit(main())
