# 01 — Detecção com o YOLO (Fase 6)

**Critério:** 5 — Sistema integrado e dashboard (3 pts) · **Depende de:** nada · **Situação:** ⬜

## Objetivo

Transformar o modelo treinado da Fase 6 num **serviço que se dispara**: recebe uma imagem e
devolve as detecções. Hoje a Fase 6 é só um notebook de treino, que demora e precisa de um dataset
que não está no repositório, então não serve para um botão.

## Tarefas

- [ ] Criar `fase6/src/detect.py`:
  - entrada: caminho de uma imagem (e limite de confiança opcional, padrão 0,25);
  - saída: imagem com as caixas desenhadas em `fase6/saidas/` e um JSON no terminal com
    `classe`, `confianca` e `caixa` de cada detecção;
  - carregar `fase6/models/best.pt` com o código do YOLOv5 no commit
    `f9578796b8a64889aa9e66dc06914d19f40d338e`, o mesmo do treino. O notebook já faz isso
    clonando o repositório em `.trabalho/yolov5/` e usando `torch.hub.load(..., source='local')`.
- [ ] Copiar 3 ou 4 imagens de teste de `Meu Drive/FarmTech_Fase6/dataset/images/test/` para
      `fase6/data/amostras/`, com a origem e a licença (CC BY 2.0) num `fase6/data/amostras/LICENCAS.md`.
- [ ] Ambiente leve para a detecção: o `uv sync` atual da Fase 6 instala TensorFlow e PyTorch
      com CUDA (vários GB). Criar um grupo de dependências `deteccao` só com PyTorch para CPU e as
      dependências do YOLOv5.
- [ ] Adicionar `saidas/` ao `.gitignore`.
- [ ] Atualizar [`docs/fases/fase6.md`](../fases/fase6.md) e o README da raiz com o comando novo.

## Critério de pronto

- `cd fase6 && uv run python src/detect.py data/amostras/<foto>.jpg` termina sem erro, imprime o
  JSON e grava a imagem anotada.
- Trator e vaca aparecem corretamente nas imagens de amostra.

## Decisões e riscos

- **Versão do YOLOv5:** outra versão pode não abrir o `best.pt` (o arquivo guarda classes do
  pacote `models.yolo`). Fixar o commit.
- **Resultado do YOLO no alerta:** opcional. Se der tempo, o `detect.py` também devolve um resumo
  que a frente [04](04-alerta-aws.md) usa (ex.: vaca na lavoura → verificar cercas).
