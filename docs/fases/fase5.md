# Fase 5 — Machine Learning e nuvem

Pasta: [`fase5/`](../../fase5/) · Vídeo da entrega original: <https://youtu.be/6JMimcQ_3hc>

## O que faz

Notebook `pbl_fase5.ipynb` sobre a base `crop_yield.csv` (rendimento de safra por cultura e
condições climáticas):

1. **Análise exploratória:** distribuições, rendimento por cultura e correlação entre variáveis.
2. **Aprendizado não supervisionado:** K-Means (cotovelo e silhueta para escolher o k) e
   Isolation Forest para achar cenários discrepantes.
3. **Aprendizado supervisionado:** cinco modelos de regressão para prever o rendimento, com
   comparação visual, previsto × real e importância das variáveis.

## A parte de AWS

A parte de nuvem da Fase 5 não foi entregue na época. Na Fase 7 ela é coberta pelo **serviço de
alerta na AWS** (Parte 2 do enunciado). Ver o
[plano de entrega](../plano-entrega/04-alerta-aws.md).

## Papel na Fase 7

O enunciado não exige a pasta da Fase 5 nem um botão para ela. Ela fica no repositório como
complemento, porque o README documenta as Fases 1 a 6.

## Como executar

```bash
cd fase5
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab pbl_fase5.ipynb
```
