"""Ir Além 1 — Reconhecimento de imagens com o Amazon Rekognition (FarmTech Solutions, Fase 7).

Envia as fotos de uma pasta ao Rekognition (DetectLabels), grava a resposta completa em JSON, desenha
as caixas que o serviço devolve e, opcionalmente, compara com o YOLOv5 treinado na Fase 6.

    python3 main.py ir-alem-1                       # fotos de fase6/data/amostras -> resultados/
    python3 main.py ir-alem-1 --comparar            # idem + roda o detect.py da Fase 6 e monta comparacao.md
    python3 main.py ir-alem-1 --pasta minhas_fotos --min-confianca 60

Credenciais: as mesmas do serviço de alerta, no .env da raiz (AWS_REGION, AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY). O usuário IAM precisa da permissão rekognition:DetectLabels. Com AWS_ENDPOINT_URL
definido (floci) o código roda, mas o emulador devolve um rótulo falso: serve só para testar a chamada.
Custo na AWS real: US$ 0,001 por imagem (DetectLabels), fora da cota permanente.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import boto3
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
AMOSTRAS = RAIZ / "fase6" / "data" / "amostras"
RESULTADOS = AQUI / "resultados"

# Rótulos do Rekognition que correspondem às classes do YOLO da Fase 6
EQUIVALENCIAS = {"vaca": {"Cow", "Cattle", "Bull", "Ox", "Calf", "Dairy Cow", "Livestock"},
                 "trator": {"Tractor", "Farm Machinery", "Agricultural Machinery", "Bulldozer", "Harvester"}}
EXTENSOES = {".jpg", ".jpeg", ".png"}


def log(msg: str) -> None:
    print(f"[rekognition] {msg}", file=sys.stderr, flush=True)


def cliente():
    load_dotenv(RAIZ / ".env")
    endpoint = os.getenv("AWS_ENDPOINT_URL")
    if endpoint:
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
        log(f"usando o emulador em {endpoint}: os rótulos NÃO são reais")
    return boto3.client("rekognition", region_name=os.getenv("AWS_REGION", "us-east-1"), endpoint_url=endpoint)


def detectar(rk, imagem: Path, max_rotulos: int, min_conf: float) -> dict:
    resposta = rk.detect_labels(Image={"Bytes": imagem.read_bytes()}, MaxLabels=max_rotulos, MinConfidence=min_conf)
    rotulos = [{"nome": l["Name"], "confianca": round(l["Confidence"], 2),
                "pais": [p["Name"] for p in l.get("Parents", [])],
                "caixas": [{k.lower(): round(v, 4) for k, v in i["BoundingBox"].items()} | {"confianca": round(i["Confidence"], 2)}
                           for i in l.get("Instances", [])]}
               for l in resposta["Labels"]]
    return {"imagem": str(imagem), "quando": datetime.now().isoformat(timespec="seconds"),
            "parametros": {"MaxLabels": max_rotulos, "MinConfidence": min_conf},
            "rotulos": rotulos, "resposta_bruta": resposta}


def desenhar(imagem: Path, resultado: dict, destino: Path) -> int:
    img = Image.open(imagem).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        fonte = ImageFont.truetype("DejaVuSans-Bold.ttf", max(14, img.width // 50))
    except OSError:
        fonte = ImageFont.load_default()
    n = 0
    for r in resultado["rotulos"]:
        for c in r["caixas"]:
            x1, y1 = c["left"] * img.width, c["top"] * img.height
            x2, y2 = x1 + c["width"] * img.width, y1 + c["height"] * img.height
            draw.rectangle([x1, y1, x2, y2], outline=(255, 140, 0), width=max(2, img.width // 300))
            texto = f"{r['nome']} {c['confianca']:.0f}%"
            tw, th = draw.textbbox((0, 0), texto, font=fonte)[2:]
            draw.rectangle([x1, y1 - th - 4, x1 + tw + 6, y1], fill=(255, 140, 0))
            draw.text((x1 + 3, y1 - th - 2), texto, fill="black", font=fonte)
            n += 1
    topo = ", ".join(f"{r['nome']} {r['confianca']:.0f}%" for r in resultado["rotulos"][:5])
    draw.rectangle([0, 0, img.width, 26], fill=(0, 0, 0))
    draw.text((6, 5), f"Rekognition: {topo}"[:120], fill="white", font=fonte)
    img.save(destino, "JPEG", quality=90)
    return n


def yolo(imagem: Path) -> dict | None:
    """Roda o detect.py da Fase 6 pelo main.py da raiz e devolve o JSON (ou None se falhar)."""
    p = subprocess.run([sys.executable, str(RAIZ / "main.py"), "fase6", str(imagem), "--saida", str(RESULTADOS / "yolo")],
                       cwd=RAIZ, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except ValueError:
        log(f"YOLO falhou em {imagem.name}: {p.stderr.strip()[-300:]}")
        return None


def classe_rekognition(rotulos: list[dict]) -> tuple[str, float]:
    """Traduz os rótulos do Rekognition para as classes da Fase 6 (vaca/trator) pelo rótulo equivalente mais confiante."""
    melhor = ("nenhum", 0.0)
    for r in rotulos:
        for classe, nomes in EQUIVALENCIAS.items():
            if r["nome"] in nomes and r["confianca"] > melhor[1]:
                melhor = (classe, r["confianca"])
    return melhor


def comparacao_md(linhas: list[dict], destino: Path) -> None:
    acertos_rk = sum(l["verdade"] == l["rekognition_classe"] for l in linhas)
    acertos_yolo = sum(l["verdade"] == l["yolo_classe"] for l in linhas if l["yolo_classe"] is not None)
    com_yolo = sum(l["yolo_classe"] is not None for l in linhas)
    md = [f"# Comparação: Amazon Rekognition × YOLOv5 da Fase 6",
          f"",
          f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por `rekognition.py --comparar`. A classe verdadeira vem do nome do",
          f"arquivo (`vaca_*.jpg`, `trator_*.jpg`); fotos com outro nome ficam sem verdade e não entram na acurácia.",
          f"",
          f"| Imagem | Verdade | Rekognition (rótulo equivalente) | Rekognition: 5 rótulos mais confiantes | Caixas Rekognition | YOLO Fase 6 (classe, confiança) |",
          f"|---|---|---|---|---|---|"]
    for l in linhas:
        md.append(f"| `{l['imagem']}` | {l['verdade'] or '—'} | {l['rekognition_classe']} ({l['rekognition_confianca']:.0f}%) | {l['top5']} | {l['caixas']} | "
                  f"{'—' if l['yolo_classe'] is None else f'{l['yolo_classe']} ({l['yolo_confianca']:.0f}%)'} |")
    md += ["",
           f"- **Rekognition:** {acertos_rk} de {len(linhas)} classes corretas.",
           f"- **YOLO da Fase 6:** {acertos_yolo} de {com_yolo} classes corretas.",
           "",
           "## Leitura",
           "",
           "- O Rekognition é um modelo **genérico, pronto**, sem treino: devolve dezenas de rótulos hierárquicos",
           "  (ex.: *Animal → Mammal → Cattle → Cow*) e caixas só para alguns rótulos comuns. Não existe a classe",
           "  \"trator\" exatamente como na Fase 6; a tabela usa rótulos equivalentes (`EQUIVALENCIAS` no script).",
           "- O YOLO da Fase 6 é **especializado** nas duas classes da fazenda: aprende o que *nós* definimos como",
           "  trator e vaca, roda offline e sem custo por imagem, mas foi treinado com 32 fotos por classe e erra em",
           "  fotos muito diferentes do dataset.",
           "- **Custo e operação:** Rekognition cobra US$ 0,001 por imagem e exige internet e credenciais; o YOLO",
           "  exige manter o modelo, o dataset e o ambiente (PyTorch).",
           "- **Quando usar cada um:** Rekognition para detectar *muitas* coisas sem treinar (pessoas, veículos,",
           "  animais, cenas) e para começar rápido; YOLO próprio quando as classes são específicas do negócio",
           "  (uma praga, um implemento, um defeito) ou quando a inferência precisa rodar na borda (ESP32-CAM, drone).",
           "- **Na FarmTech:** o serviço de alerta pode consumir qualquer um dos dois; o `alerta.py --yolo` lê o JSON",
           "  do `detect.py`, e bastaria mapear os rótulos do Rekognition para o mesmo `resumo` {vaca, trator}."]
    destino.write_text("\n".join(md), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Detecta rótulos e caixas com o Amazon Rekognition.")
    p.add_argument("--pasta", type=Path, default=AMOSTRAS, help=f"pasta com as fotos (padrão: {AMOSTRAS})")
    p.add_argument("--max-rotulos", type=int, default=15)
    p.add_argument("--min-confianca", type=float, default=50.0)
    p.add_argument("--comparar", action="store_true", help="roda também o YOLO da Fase 6 e escreve resultados/comparacao.md")
    args = p.parse_args(argv)

    fotos = sorted(f for f in args.pasta.iterdir() if f.suffix.lower() in EXTENSOES)
    if not fotos:
        sys.exit(f"Nenhuma foto em {args.pasta}")
    RESULTADOS.mkdir(exist_ok=True)
    rk = cliente()
    linhas, resumo = [], []
    for foto in fotos:
        try:
            res = detectar(rk, foto, args.max_rotulos, args.min_confianca)
        except Exception as e:  # credenciais, permissão (AccessDeniedException), rede
            sys.exit(f"Rekognition falhou em {foto.name}: {e}\nConfira AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY no .env "
                     "e se o usuário IAM tem rekognition:DetectLabels.")
        (RESULTADOS / f"{foto.stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str))
        n_caixas = desenhar(foto, res, RESULTADOS / f"{foto.stem}_rekognition.jpg")
        classe, conf = classe_rekognition(res["rotulos"])
        top5 = ", ".join(f"{r['nome']} {r['confianca']:.0f}%" for r in res["rotulos"][:5])
        log(f"{foto.name}: {len(res['rotulos'])} rótulos, {n_caixas} caixas → {classe} ({conf:.0f}%) | {top5}")
        linha = {"imagem": foto.name, "verdade": foto.stem.split("_")[0] if foto.stem.split("_")[0] in EQUIVALENCIAS else None,
                 "rekognition_classe": classe, "rekognition_confianca": conf, "top5": top5, "caixas": n_caixas,
                 "yolo_classe": None, "yolo_confianca": 0.0}
        if args.comparar:
            y = yolo(foto)
            if y and y["deteccoes"]:
                linha["yolo_classe"], linha["yolo_confianca"] = y["deteccoes"][0]["classe"], y["deteccoes"][0]["confianca"] * 100
            elif y:
                linha["yolo_classe"] = "nenhum"
        linhas.append(linha)
        resumo.append({k: linha[k] for k in ("imagem", "verdade", "rekognition_classe", "rekognition_confianca", "caixas", "yolo_classe", "yolo_confianca")})

    (RESULTADOS / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2))
    if args.comparar:
        comparacao_md(linhas, RESULTADOS / "comparacao.md")
        log(f"comparação em {RESULTADOS / 'comparacao.md'}")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
