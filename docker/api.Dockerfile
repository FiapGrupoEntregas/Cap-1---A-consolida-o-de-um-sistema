# API do AgriShield (FastAPI). Contexto de build: a **raiz** do repositório.
#
# Por que a raiz e não `api/`: os scripts de dados (`scripts/load_psr.py`) e a amostra
# versionada (`data/sample/`) ficam fora de `api/`, e é com eles que se semeia o banco
# do container. O layout aqui espelha o do repositório, então os caminhos relativos dos
# scripts continuam valendo.
#
# Build:  docker compose build api
# Direto: docker build -f docker/api.Dockerfile -t agrishield-api .

FROM python:3.12-slim

# Python em container: sem .pyc, log sem buffer (senão o `docker logs` engasga).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# `app.main` é importável de qualquer cwd, e os scripts rodam a partir de /app.
ENV PYTHONPATH=/app/api

WORKDIR /app

# As dependências vêm antes do código, para o cache do Docker não ser invalidado a
# cada edição de arquivo `.py`. `requirements.txt` é gerado por
# scripts/sync-requirements.sh — não edite à mão (CLAUDE.md). Ele exporta sem hashes
# (`uv export --no-hashes`), então não há `--require-hashes` aqui: as versões continuam
# fixadas por `==`, que é o que trava a reprodutibilidade neste projeto.
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt

# Código e dados que a API lê em runtime: o catálogo de fazendas (W1), os casos de
# replay (W9) e os artefatos do modelo (D3, ~43 KB). O dataset de treino **não** entra:
# a API carrega o artefato, nunca treina.
COPY api/app api/app
COPY api/pyproject.toml api/pyproject.toml

# Scripts e amostra do PSR, para semear o banco de dentro do container:
#   docker compose run --rm api python scripts/load_psr.py --sample
COPY scripts scripts
COPY data/sample data/sample

# Usuário sem privilégio, dono do diretório do banco. O volume é montado em /data e
# precisa ser escrevível por ele.
RUN useradd --create-home --uid 10001 agrishield \
    && mkdir -p /data \
    && chown -R agrishield:agrishield /data /app
USER agrishield

EXPOSE 8000

# A imagem não tem curl; o healthcheck usa o Python que já está aqui.
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=5 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else sys.exit(1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
