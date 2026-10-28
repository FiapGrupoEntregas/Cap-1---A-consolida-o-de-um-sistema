# Front-web do AgriShield (Streamlit). Contexto de build: a **raiz** do repositório.
#
# Build:  docker compose build front
# Direto: docker build -f docker/front.Dockerfile -t agrishield-front .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências antes do código, para preservar o cache do Docker entre edições.
COPY front-web/requirements.txt requirements.txt
RUN pip install -r requirements.txt

# O front **só exibe dados vindos da API** (CLAUDE.md): não há regra de negócio nem
# acesso a banco aqui, então basta o código da pasta.
COPY front-web/ ./

RUN useradd --create-home --uid 10001 agrishield && chown -R agrishield:agrishield /app
USER agrishield

EXPOSE 8501

# Endpoint de saúde do próprio Streamlit.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else sys.exit(1)"]

# `--server.address=0.0.0.0` é o que torna a porta alcançável de fora do container;
# `--server.headless=true` evita o Streamlit tentar abrir navegador e pedir e-mail.
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
