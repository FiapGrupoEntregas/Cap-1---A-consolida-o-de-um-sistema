# Fase 6 — Visão computacional com YOLO

Pasta: [`fase6/`](../../fase6/) · Vídeo da entrega original: <https://youtu.be/fHTtq75ch_g>

## O que faz

Detecta **tratores** e **vacas** em imagens com um **YOLOv5s** ajustado (fine-tuning) a partir dos
pesos do COCO, e compara essa abordagem com o YOLO padrão e com uma CNN treinada do zero. O passo
a passo, os gráficos e as conclusões estão no notebook
[`src/JonattasFelipe_rm572692_pbl_fase6.ipynb`](../../fase6/src/JonattasFelipe_rm572692_pbl_fase6.ipynb).

## Dataset

- 80 imagens do **Open Images V7** (Google): 40 de trator e 40 de vaca, divididas em 32 de treino,
  4 de validação e 4 de teste por classe.
- Fotos com licença CC BY 2.0 e anotações com licença CC BY 4.0.
- Caixas pré-rotuladas (caixas humanas do Open Images para vaca; YOLO-World para trator) e
  revisadas à mão no Make Sense.
- O dataset não está neste repositório. Ele está no Google Drive de quem rodou o notebook
  (`Meu Drive/FarmTech_Fase6/dataset/`); o notebook também consegue remontá-lo do zero.

## Modelos

| Modelo | Origem | Papel |
|---|---|---|
| YOLOv5s customizado | `ultralytics/yolov5` + pesos `yolov5s.pt` do COCO | Detecção de trator e vaca (Entrega 1), treinado com 30 e 60 épocas |
| YOLO padrão | pesos do COCO, sem treino | Comparação (Entrega 2) |
| CNN própria | Keras / TensorFlow | Classificação treinada do zero (Entrega 2) |
| YOLO-World | `yolov8s-worldv2.pt` | Só para pré-rotular as caixas de trator |

## Pesos treinados: `models/best.pt`

Conferido em 08/11/2026 lendo os metadados do arquivo:

| Item | Valor |
|---|---|
| Classes | `0: trator`, `1: vaca` |
| Treino | YOLOv5s, simulação de 30 épocas (`exp_30ep`), imagens de 640 px, lote 8 |
| Data | 13/10/2026, no Google Colab |
| Versão do YOLOv5 | commit `f9578796b8a64889aa9e66dc06914d19f40d338e` |

Para carregar os pesos é preciso o código do YOLOv5 nesse mesmo commit.

## IA generativa usada na entrega original

| Modelo | Uso |
|---|---|
| Claude Sonnet 5.5 (Anthropic) | Revisão do notebook e do README, sugestões de correção e apoio na redação das conclusões |
| Claude Opus 5.5 (Claude Code) | Migração do ambiente para uv, correção do download do dataset, pré-rotulação automática e documentação |

## Como executar

```bash
cd fase6
uv sync                    # Python 3.12, PyTorch, TensorFlow e Jupyter
uv run jupyter lab         # abrir src/JonattasFelipe_rm572692_pbl_fase6.ipynb
```

No Google Colab, o notebook monta o Drive e salva os resultados em `Meu Drive/FarmTech_Fase6/`.
Sem GPU, o treino na CPU é bem mais lento.
