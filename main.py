#!/usr/bin/env python3
"""FarmTech Solutions — Fase 7: dispara qualquer serviço das Fases 1 a 6 pelo terminal.

    python3 main.py listar                      # mostra os serviços
    python3 main.py fase6 fase6/data/amostras/vaca_02.jpg
    python3 main.py fase1-calculo -- --cultura manga --largura 100 --comprimento 200 --ruas 10 --litros-por-metro 0.5

Só usa a biblioteca padrão: roda com qualquer `python3`, sem instalar nada. Cada fase executa no
próprio ambiente (`uv run --project <pasta>`), então as dependências não se misturam. A dashboard
central (fase4/src/app.py) chama este mesmo arquivo nos botões.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = RAIZ / ".env"


@dataclass(frozen=True)
class Servico:
    nome: str
    descricao: str
    pasta: str                      # cwd relativo à raiz
    comando: list[str]              # comando a executar
    precisa: tuple[str, ...] = ()   # "uv", "r", "env", "docker"
    args: str = ""                  # argumentos extras aceitos (ajuda)
    detalhe: str = ""               # dica mostrada antes de rodar


def uv(projeto: str, *cmd: str) -> list[str]:
    return ["uv", "run", "--project", str(RAIZ / projeto), *cmd]


SERVICOS: dict[str, Servico] = {s.nome: s for s in [
    Servico("fase1", "Fase 1 · programa interativo de área de plantio e insumos (manga e cana), dados em CSV",
            "fase1/src", uv("fase1/src", "main.py"), ("uv",)),
    Servico("fase1-calculo", "Fase 1 · cálculo de área e insumos sem perguntas; devolve JSON (usado pela dashboard)",
            "fase1/src", uv("fase1/src", "python", "calculo.py"), ("uv",),
            args="--cultura manga|cana e as medidas (veja `-- --help`)"),
    Servico("fase1-estatistica", "Fase 1 · estatística dos registros do CSV em R",
            "fase1/src", ["Rscript", "Rscripts/python-consumer.r"], ("r",)),
    Servico("fase1-clima", "Fase 1 · previsão do tempo (Open-Meteo) em R",
            "fase1/src", ["Rscript", "Rscripts/weather-getter.r"], ("r",)),
    Servico("fase2-clima", "Fase 2 · previsão de chuva e código S/L/C para o ESP32 de irrigação",
            "fase2", uv("fase2", "python", "src/main.py"), ("uv",)),
    Servico("fase2-regressao", "Fase 2 · regressão logística da decisão de irrigar, em R",
            "fase2", ["Rscript", "src/irrigacao.r"], ("r",)),
    Servico("fase3-consultas", "Fase 3 · roda as consultas de consulta.sql no Oracle e imprime as tabelas",
            "fase3", uv("fase3/dashboard", "python", "consultas.py"), ("uv", "env"),
            args="[--sql outro.sql] [--json]"),
    Servico("fase3-dashboard", "Fase 3 · dashboard Streamlit do Oracle (porta 8502)",
            "fase3/dashboard", uv("fase3/dashboard", "streamlit", "run", "app.py", "--server.port", "8502"),
            ("uv", "env"), detalhe="Abra http://localhost:8502 · Ctrl+C para parar"),
    Servico("fase4-api", "Fase 4 · API FastAPI que recebe as leituras do ESP32 e grava no Oracle (porta 8000)",
            "fase4/src", uv("fase4/src", "uvicorn", "api:app", "--port", "8000"), ("uv", "env"),
            detalhe="Documentação em http://localhost:8000/docs · Ctrl+C para parar"),
    Servico("fase4-dashboard", "Fase 4 · dashboard central (Streamlit): análise de solo, previsão e central de serviços",
            "fase4/src", uv("fase4/src", "streamlit", "run", "app.py"), ("uv", "env"),
            detalhe="Precisa da API (fase4-api) no ar · Ctrl+C para parar"),
    Servico("fase6", "Fase 6 · detecta trator e vaca numa imagem com o YOLOv5 treinado; devolve JSON",
            "fase6", uv("fase6", "python", "src/detect.py"), ("uv",),
            args="<imagem> [--conf 0.25] [--saida pasta]"),
    Servico("alerta", "Fase 7 · avalia as últimas leituras (Oracle SOIL_DATA) e publica os alertas com ação corretiva no SNS",
            "alerta", uv("alerta", "python", "alerta.py"), ("uv", "env"),
            args="[--ultimas N] [--fonte api] [--simular seco|acido|alcalino|npk|tudo|ok] [--yolo x.json] [--dry-run] [--forcar]"),
    Servico("ir-alem-1", "Ir Além 1 · envia fotos ao Amazon Rekognition (DetectLabels), anota as caixas e compara com o YOLO da Fase 6",
            "IR-ALEM/ir-alem-1", uv("IR-ALEM/ir-alem-1", "python", "rekognition.py"), ("uv", "env"),
            args="[--pasta fotos] [--comparar] [--min-confianca 50]"),
    Servico("alerta-floci","Fase 7 · prepara/inspeciona o SNS do floci (AWS local): preparar | ler | limpar",
            "alerta", uv("alerta", "python", "floci.py"), ("uv", "docker"),
            args="preparar | ler [--manter] | limpar", detalhe="Precisa do floci no ar: `docker compose up -d`"),
]}


def erro(msg: str, codigo: int = 1) -> int:
    print(f"[main.py] {msg}", file=sys.stderr)
    return codigo


def verificar(servico: Servico) -> int | None:
    """Confere o que o serviço precisa; devolve o código de erro ou None se estiver tudo certo."""
    if "uv" in servico.precisa and not shutil.which("uv"):
        return erro("`uv` não encontrado. Instale em https://docs.astral.sh/uv/ e rode de novo.")
    if "r" in servico.precisa and not shutil.which("Rscript"):
        return erro("`Rscript` não encontrado. Instale o R (https://cran.r-project.org/) para este serviço.")
    if "env" in servico.precisa and not ENV.exists():
        return erro(f"Arquivo .env não encontrado em {RAIZ}. Rode `cp .env.example .env` e preencha "
                    "ORACLE_USER e ORACLE_PASSWORD (RM e senha do Oracle da FIAP).")
    if "docker" in servico.precisa and not shutil.which("docker"):
        return erro("`docker` não encontrado; necessário para o floci (AWS local).")
    return None


def executar(servico: Servico, extras: list[str]) -> int:
    if not servico.comando:
        return erro(f"Serviço `{servico.nome}` ainda não está disponível. {servico.detalhe}", 3)
    if (codigo := verificar(servico)) is not None:
        return codigo
    if servico.detalhe:
        print(f"[main.py] {servico.detalhe}", file=sys.stderr)
    # O serviço roda dentro da pasta da fase; caminhos relativos digitados pelo usuário (ex.: uma
    # imagem para a fase6) são convertidos para absolutos antes, senão deixariam de existir lá.
    extras = [str(Path(a).resolve()) if not a.startswith("-") and Path(a).exists() else a for a in extras]
    comando = [*servico.comando, *extras]
    print(f"[main.py] {servico.nome}: {' '.join(comando)}", file=sys.stderr)
    try:
        resultado = subprocess.run(comando, cwd=RAIZ / servico.pasta, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    except KeyboardInterrupt:
        print(f"\n[main.py] {servico.nome} interrompido.", file=sys.stderr)
        return 130
    except FileNotFoundError as e:
        return erro(f"Não consegui executar `{comando[0]}`: {e}")
    if resultado.returncode not in (0, 2, 4):  # 2 = fase6 sem detecções; 4 = alerta não publicado (já explicado no JSON)
        dica = ""
        if "env" in servico.precisa:
            dica = " Se o erro for de conexão (ORA-/DPY-), confira o .env e se o Oracle da FIAP está acessível."
        print(f"[main.py] {servico.nome} terminou com código {resultado.returncode}.{dica}", file=sys.stderr)
    return resultado.returncode


def listar() -> int:
    largura = max(len(n) for n in SERVICOS)
    print("Serviços disponíveis (python3 main.py <serviço> [-- argumentos]):\n")
    for s in SERVICOS.values():
        estado = "" if s.comando else "  [em construção]"
        print(f"  {s.nome.ljust(largura)}  {s.descricao}{estado}")
        if s.args:
            print(f"  {' ' * largura}  argumentos: {s.args}")
    print("\nPré-requisitos: uv (todas as fases Python), R (fase1-estatistica, fase1-clima, fase2-regressao),"
          "\n.env na raiz (fase3-*, fase4-*). Detalhes em COMO_USAR.md.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="main.py", description="Dispara os serviços da FarmTech Solutions (Fases 1 a 6).",
                                     epilog="Argumentos para o serviço vão depois de `--`, ou direto após o nome.")
    parser.add_argument("servico", nargs="?", default="listar", help="nome do serviço, ou `listar`")
    parser.add_argument("extras", nargs=argparse.REMAINDER, help="argumentos repassados ao serviço")
    args = parser.parse_args(argv)

    if args.servico in ("listar", "list", "ls"):
        return listar()
    if args.servico not in SERVICOS:
        proximos = [n for n in SERVICOS if n.startswith(args.servico.split("-")[0])]
        dica = f" Parecidos: {', '.join(proximos)}." if proximos else ""
        return erro(f"Serviço `{args.servico}` não existe. Use `python3 main.py listar`.{dica}", 2)
    extras = args.extras[1:] if args.extras[:1] == ["--"] else args.extras
    return executar(SERVICOS[args.servico], extras)


if __name__ == "__main__":
    sys.exit(main())
