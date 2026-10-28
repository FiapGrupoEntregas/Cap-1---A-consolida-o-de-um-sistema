#!/usr/bin/env bash
# Leva a base real do PSR já carregada na SUA máquina para dentro do banco do container.
#
# O problema que isto resolve: `scripts/load_psr.py` rodado no host grava em
# `api/agrishield.db`. A API em container usa **outro** banco — um volume do Docker. Por isso
# os relatórios aparecem zerados mesmo depois de você ter carregado o PSR.
#
# Este script copia **apenas a tabela `policy`**, preservando o que já existe no volume:
# máquinas cadastradas, telemetria, eventos e trilha de auditoria continuam lá.
#
# Uso:
#   ./scripts/importar-psr-no-docker.sh
#
# Alternativa, se você não tem a base completa: semear a amostra versionada, bem menor.
#   docker compose run --rm api python scripts/load_psr.py --sample

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BANCO_HOST="$RAIZ/api/agrishield.db"
VOLUME="agrishield_agrishield-db"
# O Dockerfile cria o usuário `agrishield` com este uid; o banco do volume pertence a ele.
UID_CONTAINER=10001

vermelho() { printf '\033[31m%s\033[0m\n' "$*"; }
verde()    { printf '\033[32m%s\033[0m\n' "$*"; }

if [ ! -f "$BANCO_HOST" ]; then
  vermelho "Não encontrei $BANCO_HOST."
  echo "Carregue a base no host antes:"
  echo "    uv run --project api python scripts/download_psr.py"
  echo "    uv run --project api python scripts/load_psr.py"
  echo
  echo "Ou, se quiser só a amostra versionada (mais rápido, e dispensa este script):"
  echo "    docker compose run --rm api python scripts/load_psr.py --sample"
  exit 1
fi

if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  vermelho "O volume $VOLUME não existe."
  echo "Suba a pilha ao menos uma vez: docker compose up -d"
  exit 1
fi

echo "Parando a API para ninguém escrever no banco durante a cópia..."
(cd "$RAIZ" && docker compose stop api >/dev/null 2>&1) || true

echo "Copiando a tabela \`policy\`..."
# Roda como root de propósito: o banco do host é seu e o do volume é do uid 10001 —
# nenhum usuário comum escreve nos dois. A posse é devolvida logo em seguida.
docker run --rm \
  -v "$VOLUME:/destino" \
  -v "$RAIZ/api:/origem" \
  python:3.12-slim \
  sh -c "
    python - <<'PY'
import sqlite3, time
inicio = time.time()
con = sqlite3.connect('/destino/agrishield.db')
con.execute('ATTACH DATABASE \"/origem/agrishield.db\" AS origem')
antes = con.execute('select count(*) from policy').fetchone()[0]
if antes:
    print(f'  o volume já tinha {antes} apólices; elas serão substituídas')
    con.execute('DELETE FROM policy')
con.execute('INSERT INTO policy SELECT * FROM origem.policy')
con.commit()
depois = con.execute('select count(*) from policy').fetchone()[0]
print(f'  {depois} apólices no banco do container ({time.time() - inicio:.1f}s)')
con.close()
PY
    chown -R $UID_CONTAINER:$UID_CONTAINER /destino
  "

echo "Subindo a API de volta..."
(cd "$RAIZ" && docker compose up -d api >/dev/null)

for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/api/v1/health >/dev/null 2>&1; then break; fi
  sleep 1
done

echo
verde "Pronto. Confira os relatórios:"
echo "    curl -s localhost:8000/api/v1/reports/crop | head -c 200"
echo "    http://localhost:8501 → aba Relatórios"
