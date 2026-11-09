# 02 — Comandos de terminal (`main.py` na raiz)

**Critério:** 5 — Sistema integrado e dashboard (3 pts) · **Depende de:** [01](01-fase6-deteccao.md) (comando da Fase 6) · **Situação:** ⬜

## Objetivo

Um único ponto de entrada no terminal que dispara cada serviço: `python3 main.py <serviço>`. O
enunciado aceita **botão ou comando de terminal**; ter os dois custa pouco e o `main.py` vira a
fonte única de "como rodar cada fase", reaproveitada pela dashboard ([03](03-dashboard-central.md)).

## Serviços

| Comando | O que roda |
|---|---|
| `main.py listar` | Lista os serviços disponíveis |
| `main.py fase1` | Programa de terminal de área e insumos (interativo) |
| `main.py fase1-calculo --cultura manga ...` | Cálculo sem `input()`, para a dashboard (ver [03](03-dashboard-central.md)) |
| `main.py fase1-estatistica` | `Rscript Rscripts/python-consumer.r` |
| `main.py fase1-clima` | `Rscript Rscripts/weather-getter.r` |
| `main.py fase2-clima` | Código S/L/C da previsão do tempo |
| `main.py fase2-regressao` | Regressão logística em R |
| `main.py fase3-consultas` | Executa as consultas de `consulta.sql` no Oracle e imprime as tabelas |
| `main.py fase3-dashboard` | Sobe o Streamlit da Fase 3 na porta 8502 |
| `main.py fase4-api` | Sobe a API da Fase 4 na porta 8000 |
| `main.py fase4-dashboard` | Sobe a dashboard central (Fase 4 evoluída) |
| `main.py fase6 <imagem>` | Detecção com o YOLO |
| `main.py alerta` | Avalia as últimas leituras e publica os alertas (frente [04](04-alerta-aws.md)) |

## Tarefas

- [ ] Criar `main.py` só com a biblioteca padrão (`argparse`, `subprocess`, `pathlib`), para rodar
      com qualquer `python3` sem instalar nada.
- [ ] Cada fase roda no seu próprio ambiente com `uv run --project <pasta>`. Isso evita conflito de
      dependências (a Fase 6 traz PyTorch e TensorFlow) e impede o `uv` de procurar projetos fora
      do repositório.
- [ ] Mensagens claras quando faltar algo (R não instalado, `.env` ausente, Oracle fora do ar).
- [ ] Repassar a saída de cada serviço para o terminal e devolver o código de saída.
- [ ] Documentar os comandos no README da raiz (seção "Como executar").

## Critério de pronto

- `python3 main.py listar` mostra todos os serviços.
- Os comandos das Fases 1, 2, 3 e 6 rodam num clone novo, depois de `cp .env.example .env`.
