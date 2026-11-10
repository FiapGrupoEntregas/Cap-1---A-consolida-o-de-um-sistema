# 06 — Ir Além (opcional)

**Situação:** 🟨 Ir Além 2 pronto (falta o vídeo); Ir Além 1 com código e documentação prontos, falta rodar na AWS (ver [cronograma](cronograma-aws.md)).

Os dois desafios vão na pasta `IR-ALEM/` do mesmo repositório, cada um com um vídeo de até
4 minutos (não listado) cujo link entra no `.txt` e no README.

## Ir Além 1 — AWS Rekognition

- [x] Código: `IR-ALEM/ir-alem-1/rekognition.py` (DetectLabels em cada foto, JSON, imagem anotada,
      `--comparar` com o YOLO da Fase 6 → `resultados/comparacao.md`), `main.py ir-alem-1`. Testado no
      floci (chamada válida; rótulos falsos, por isso `resultados/` fica vazio até a execução real).
- [x] Figura autoral da arquitetura e justificativa crítica em `IR-ALEM/README.md`.
- [x] Rodado na AWS real em 10/11/2026: 4/4 classes nos dois; Rekognition 81–99,9 %, YOLO 60–84 %;
      Rekognition sem caixa no trator. `resultados/` pronta para commitar.
- [ ] Prints em `IR-ALEM/ir-alem-1/prints/` (lista e campos explicados em `IR-ALEM/README.md`).
- [ ] Vídeo de até 4 min (não listado).

## Ir Além 2 — Algoritmo genético

- [x] Notebook `IR-ALEM/ir-alem-2/ir_alem_2_algoritmo_genetico.ipynb`: mochila binária de intervenções
      (irrigar, calagem, enxofre, adubar N/P/K) por talhão com orçamento de 35 % do custo, montada das
      leituras reais de `SOIL_DATA` (Fase 4) e das regras do alerta.
- [x] Entrada em `dados/talhoes.csv` (gerada por `gerar_dados.py` com semente fixa); o notebook só lê o arquivo.
- [x] 2 variantes de cada operador (torneio/roleta, um ponto/uniforme, bit-flip/troca) = 8 configurações ×
      10 sementes, comparadas em aptidão e tempo; validação com força bruta (18 itens) e heurística gulosa.
- [x] Tabela de parâmetros com justificativa, figura autoral da arquitetura (`figuras/01-arquitetura.png`)
      e 4 figuras de resultados. Resumo em `IR-ALEM/README.md`.
- [ ] Vídeo de até 4 min (não listado): problema → dados → AG → comparação → plano final.

**Nota sobre o Ir Além 1:** o Rekognition do floci devolve um rótulo falso ("Floci", 99,9 %) para qualquer
imagem e não implementa coleções, então não serve de evidência. Na AWS real o `DetectLabels` custa
US$ 0,001 por imagem (sem cota permanente); analisar as amostras da Fase 6 custa centavos. Se for feito,
aproveitar a sessão da frente [04](04-alerta-aws.md): mesma conta, orçamento e usuário IAM (acrescentar
`rekognition:DetectLabels`).
