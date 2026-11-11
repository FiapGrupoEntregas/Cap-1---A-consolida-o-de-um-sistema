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

Para carregar os pesos é preciso o código do YOLOv5 nesse mesmo commit. O arquivo também foi salvo
com Python 3.13, por isso o `detect.py` registra um alias `pathlib._local` antes de abri-lo em
versões anteriores do Python.

## Serviço de detecção: `src/detect.py` (Fase 7)

Criado em 08/11/2026 para a Fase 7: transforma o modelo treinado num serviço que recebe uma imagem e
devolve as detecções, sem precisar do notebook nem do dataset.

```bash
cd fase6
uv sync                                                # 1ª vez: PyTorch para CPU + YOLOv5 (~1,5 GB)
uv run python src/detect.py data/amostras/vaca_02.jpg  # --conf 0.25 e --saida saidas/ são os padrões
```

- **Entrada:** caminho de uma imagem (`jpg`/`png`); `--conf` muda a confiança mínima (padrão 0,25).
- **Saída no terminal (stdout):** um JSON com `deteccoes` (classe, confiança, caixa em pixels),
  `resumo` (quantidade por classe), `acoes_sugeridas` (texto que o alerta da AWS pode usar) e o
  caminho da imagem anotada. Os logs do YOLOv5 vão para o stderr, então o JSON pode ser lido por
  outro programa (`main.py` da raiz e a dashboard).
- **Imagem anotada:** gravada em `fase6/saidas/` (pasta ignorada pelo git).
- **Código de saída:** `0` com detecções, `2` quando nada foi detectado.
- **Na 1ª execução** o script clona o YOLOv5 no commit do treino em `fase6/.trabalho/yolov5/`
  (também ignorada pelo git), igual ao notebook; precisa de `git` e internet.

### Imagens de amostra: `data/amostras/`

Quatro fotos do Wikimedia Commons (licenças em [`LICENCAS.md`](../../fase6/data/amostras/LICENCAS.md)),
escolhidas entre as que o modelo reconhece com confiança acima de 0,25:

| Imagem | Resultado em 08/11/2026 |
|---|---|
| `trator_01.jpg` | 1 trator (0,61) |
| `trator_02.jpg` | 1 trator (0,74) |
| `vaca_01.jpg` | 1 vaca (0,61) |
| `vaca_02.jpg` | 1 vaca (0,84) |

O modelo foi treinado com só 32 fotos por classe, então em fotos de outra origem a confiança cai:
de 28 fotos do Commons testadas, 7 ficaram abaixo de 0,25 e uma trouxe um falso positivo (parede
de um silo marcada como trator). É um bom exemplo para a discussão crítica no vídeo. As imagens de
teste do dataset original (`Meu Drive/FarmTech_Fase6/dataset/images/test/`) podem ser copiadas
para a mesma pasta.

## IA generativa usada na entrega original

| Modelo | Uso |
|---|---|
| Claude Sonnet 5.5 (Anthropic) | Revisão do notebook e do README, sugestões de correção e apoio na redação das conclusões |
| Claude Opus 5.5 (Claude Code) | Migração do ambiente para uv, correção do download do dataset, pré-rotulação automática e documentação |

## Como executar

```bash
cd fase6
uv sync                          # só a detecção: PyTorch para CPU e dependências do YOLOv5
uv run python src/detect.py data/amostras/trator_01.jpg

uv sync --group notebook         # treino e comparação: + TensorFlow, scikit-learn e Jupyter
uv run jupyter lab               # abrir src/JonattasFelipe_rm572692_pbl_fase6.ipynb
```

O `pyproject.toml` fixa o PyTorch para CPU no Linux e no Windows (índice `download.pytorch.org/whl/cpu`),
porque localmente só fazemos inferência; o treino de verdade foi no Google Colab com GPU. No Colab,
o notebook monta o Drive e salva os resultados em `Meu Drive/FarmTech_Fase6/`.
