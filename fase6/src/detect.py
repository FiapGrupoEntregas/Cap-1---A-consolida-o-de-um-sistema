"""Detecção de trator e vaca com o YOLOv5 customizado da Fase 6 (FarmTech Solutions).

Uso (a partir de fase6/):
    uv run python src/detect.py data/amostras/trator_01.jpg
    uv run python src/detect.py foto.jpg --conf 0.4 --saida outra_pasta

Saída:
    - no terminal (stdout): um JSON com as detecções (classe, confiança e caixa em pixels),
      um resumo por classe e o caminho da imagem anotada;
    - em fase6/saidas/: a imagem com as caixas desenhadas.

O modelo (models/best.pt) foi treinado com o código do YOLOv5 no commit abaixo. O arquivo .pt guarda
referências às classes do pacote `models` do YOLOv5, então o mesmo código precisa estar disponível
para abri-lo: na primeira execução o repositório é clonado em .trabalho/yolov5/ (pasta ignorada pelo
git), exatamente como o notebook de treino faz.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Impede o YOLOv5 de tentar instalar pacotes com pip ao carregar o modelo (o ambiente é gerido pelo uv)
os.environ.setdefault("YOLOv5_AUTOINSTALL", "False")
# O best.pt foi salvo no Colab com Python 3.13, cujo pickle referencia `pathlib._local.PosixPath`.
# Em Python <= 3.12 esse módulo não existe: o alias abaixo faz o unpickler encontrar a classe no `pathlib`.
sys.modules.setdefault("pathlib._local", pathlib)

FASE6 = Path(__file__).resolve().parents[1]
MODELO = FASE6 / "models" / "best.pt"
YOLO_DIR = FASE6 / ".trabalho" / "yolov5"
YOLO_REPO = "https://github.com/ultralytics/yolov5"
YOLO_COMMIT = "f9578796b8a64889aa9e66dc06914d19f40d338e"  # mesmo commit do treino (notebook, seção 2)
SAIDAS = FASE6 / "saidas"
IMG = 640  # tamanho de inferência usado no treino

# Sugestão de ação para o serviço de alertas (frente 04): o detect.py só descreve o que viu
ACOES = {
    "vaca": "animal na área monitorada: verificar cercas e afastar o rebanho da lavoura",
    "trator": "máquina em operação na área: registrar a atividade e conferir se estava programada",
}


def log(msg: str) -> None:
    """Mensagens de progresso vão para stderr; o stdout fica só com o JSON."""
    print(msg, file=sys.stderr, flush=True)


def garantir_yolov5() -> Path:
    """Clona o YOLOv5 no commit do treino, se ainda não estiver em .trabalho/yolov5/."""
    if not (YOLO_DIR / "hubconf.py").exists():
        log(f"Baixando o YOLOv5 ({YOLO_COMMIT[:7]}) em {YOLO_DIR} ...")
        YOLO_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", YOLO_REPO, str(YOLO_DIR)], check=True)
    atual = subprocess.run(["git", "-C", str(YOLO_DIR), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    if atual.stdout.strip() != YOLO_COMMIT:
        subprocess.run(["git", "-C", str(YOLO_DIR), "fetch", "-q"], check=False)
        subprocess.run(["git", "-C", str(YOLO_DIR), "checkout", "-q", YOLO_COMMIT], check=True)
    return YOLO_DIR


def carregar_modelo(conf: float):
    """Carrega o best.pt com o código local do YOLOv5 (torch.hub, source='local')."""
    if not MODELO.exists():
        sys.exit(f"Modelo não encontrado: {MODELO}. Copie o best.pt treinado na Fase 6 para fase6/models/.")
    import contextlib
    import logging

    import torch  # importado aqui para o --help ser instantâneo

    torch.hub.set_dir(str(FASE6 / ".trabalho" / "torch_hub"))
    with contextlib.redirect_stdout(sys.stderr):  # o YOLOv5 imprime no stdout; aqui o stdout é só do JSON
        modelo = torch.hub.load(str(garantir_yolov5()), "custom", path=str(MODELO), source="local", verbose=False)
    for handler in logging.getLogger("yolov5").handlers:  # idem para o logger criado na importação
        if isinstance(handler, logging.StreamHandler):
            handler.setStream(sys.stderr)
    modelo.conf = conf
    return modelo


def detectar(imagem: Path, conf: float = 0.25, saida: Path = SAIDAS) -> dict:
    """Roda o modelo numa imagem, grava a versão anotada e devolve o resultado como dicionário."""
    if not imagem.is_file():
        sys.exit(f"Imagem não encontrada: {imagem}")
    modelo = carregar_modelo(conf)
    resultado = modelo(str(imagem), size=IMG)

    deteccoes = []
    for *caixa, confianca, classe in resultado.xyxy[0].tolist():
        x1, y1, x2, y2 = (round(v) for v in caixa)
        deteccoes.append({"classe": modelo.names[int(classe)], "confianca": round(confianca, 3),
                          "caixa": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}})
    deteccoes.sort(key=lambda d: -d["confianca"])

    resumo = {nome: sum(d["classe"] == nome for d in deteccoes) for nome in modelo.names.values()}
    acoes = [ACOES[nome] for nome, qtd in resumo.items() if qtd and nome in ACOES]

    saida.mkdir(parents=True, exist_ok=True)
    anotada = saida / f"{imagem.stem}_{datetime.now():%Y%m%d-%H%M%S}.jpg"
    resultado.render()  # desenha as caixas em resultado.ims
    from PIL import Image

    Image.fromarray(resultado.ims[0]).save(anotada, "JPEG", quality=92)

    return {"imagem": str(imagem), "imagem_anotada": str(anotada), "limite_confianca": conf,
            "deteccoes": deteccoes, "resumo": resumo, "acoes_sugeridas": acoes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detecta trator e vaca numa imagem com o YOLOv5 da Fase 6.")
    parser.add_argument("imagem", type=Path, help="caminho da imagem (jpg/png)")
    parser.add_argument("--conf", type=float, default=0.25, help="confiança mínima das detecções (padrão 0.25)")
    parser.add_argument("--saida", type=Path, default=SAIDAS, help=f"pasta da imagem anotada (padrão {SAIDAS})")
    args = parser.parse_args(argv)

    resultado = detectar(args.imagem, args.conf, args.saida)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["deteccoes"] else 2  # código 2: nada detectado (útil para scripts)


if __name__ == "__main__":
    sys.exit(main())
