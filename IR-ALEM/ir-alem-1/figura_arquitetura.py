"""Figura autoral da arquitetura do Ir Além 1: `uv run python figura_arquitetura.py` -> figuras/01-arquitetura.png"""

from pathlib import Path

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 4.2)); ax.axis("off")
caixas = [
    ("Fotos do campo\n(fase6/data/amostras,\ndrone ou ESP32-CAM)", "#dbe9f6"),
    ("rekognition.py\nboto3 · credenciais do .env\n(usuário IAM: DetectLabels)", "#fdebd0"),
    ("Amazon Rekognition\nDetectLabels\nrótulos + caixas + confiança", "#f6dbdb"),
    ("resultados/\nJSON por foto · imagem anotada\nresumo.json", "#e8f3dc"),
    ("comparacao.md\nRekognition × YOLOv5 (Fase 6)\nacurácia, custo, operação", "#e8f3dc"),
]
for i, (txt, cor) in enumerate(caixas):
    x = 0.02 + i * 0.197
    ax.add_patch(plt.Rectangle((x, 0.33), 0.18, 0.44, fc=cor, ec="#555", lw=1, transform=ax.transAxes))
    ax.text(x + 0.09, 0.55, txt, ha="center", va="center", fontsize=8.6, transform=ax.transAxes)
    if i < len(caixas) - 1:
        ax.annotate("", xy=(x + 0.197, 0.55), xytext=(x + 0.18, 0.55), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="#555"))
ax.add_patch(plt.Rectangle((0.22, 0.04), 0.57, 0.17, fc="#f3f3f3", ec="#999", lw=0.8, ls="--", transform=ax.transAxes))
ax.text(0.505, 0.125, "Mesma conta, orçamento e usuário IAM do serviço de alerta (frente 04). "
        "Opcional: mapear os rótulos para {vaca, trator} e alimentar o alerta.py", ha="center", va="center",
        fontsize=8, transform=ax.transAxes)
ax.text(0.5, 0.9, "Ir Além 1 — FarmTech Solutions: reconhecimento de imagens com o Amazon Rekognition",
        ha="center", fontsize=10.5, transform=ax.transAxes)
Path("figuras").mkdir(exist_ok=True)
fig.savefig("figuras/01-arquitetura.png", dpi=120, bbox_inches="tight")
print("figuras/01-arquitetura.png")
