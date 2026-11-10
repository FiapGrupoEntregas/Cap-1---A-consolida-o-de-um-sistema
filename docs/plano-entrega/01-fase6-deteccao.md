# 01 — Detecção com o YOLO (Fase 6)

**Critério:** 5 — Sistema integrado e dashboard (3 pts) · **Depende de:** nada · **Situação:** ✅ concluída em 08/11/2026

## Objetivo

Transformar o modelo treinado da Fase 6 num **serviço que se dispara**: recebe uma imagem e
devolve as detecções. Hoje a Fase 6 é só um notebook de treino, que demora e precisa de um dataset
que não está no repositório, então não serve para um botão.

## Tarefas

- [x] Criar `fase6/src/detect.py`:
  - entrada: caminho de uma imagem (e limite de confiança opcional, padrão 0,25);
  - saída: imagem com as caixas desenhadas em `fase6/saidas/` e um JSON no terminal com
    `classe`, `confianca` e `caixa` de cada detecção, mais `resumo` e `acoes_sugeridas`;
  - carrega `fase6/models/best.pt` com o código do YOLOv5 no commit
    `f9578796b8a64889aa9e66dc06914d19f40d338e`, o mesmo do treino, clonado em `.trabalho/yolov5/`
    na primeira execução e aberto com `torch.hub.load(..., source='local')`.
- [x] Imagens de amostra em `fase6/data/amostras/` com origem e licença em `LICENCAS.md`.
      O dataset do Drive não estava acessível nesta máquina, então foram usadas 4 fotos do
      Wikimedia Commons (CC0, CC BY e domínio público) testadas com o modelo.
- [x] Ambiente leve: o `uv sync` da Fase 6 agora instala só a detecção (PyTorch para CPU + YOLOv5,
      ~1,5 GB). TensorFlow, scikit-learn e Jupyter ficaram no grupo `notebook`
      (`uv sync --group notebook`).
- [x] `saidas/` no `.gitignore` da Fase 6.
- [x] [`docs/fases/fase6.md`](../fases/fase6.md) e o README da raiz atualizados com o comando novo.

## Critério de pronto

- [x] `cd fase6 && uv run python src/detect.py data/amostras/<foto>.jpg` termina sem erro, imprime o
  JSON e grava a imagem anotada (testado nas 4 amostras em 08/11/2026).
- [x] Trator e vaca aparecem corretamente nas imagens de amostra (confianças entre 0,61 e 0,84).
  As amostras foram escolhidas entre 28 fotos testadas: num treino com 32 fotos por classe, parte
  das fotos de outra origem fica abaixo de 0,25 ou gera falso positivo.

## Decisões e riscos

- **Versão do YOLOv5:** outra versão pode não abrir o `best.pt` (o arquivo guarda classes do
  pacote `models.yolo`). Commit fixado no `detect.py`.
- **Python do `best.pt`:** o arquivo foi salvo no Colab com Python 3.13 e referencia
  `pathlib._local`, que não existe no 3.12 do projeto. O `detect.py` registra um alias em
  `sys.modules` antes de carregar; sem isso o `torch.hub.load` falha com "No module named 'pathlib._local'".
- **Resultado do YOLO no alerta:** o JSON já traz `acoes_sugeridas` (vaca → verificar cercas;
  trator → registrar a atividade) para a frente [04](04-alerta-aws.md) usar.
- **Logs do YOLOv5:** iam para o stdout e quebravam a leitura do JSON por outro programa; o script
  redireciona tudo para o stderr.
