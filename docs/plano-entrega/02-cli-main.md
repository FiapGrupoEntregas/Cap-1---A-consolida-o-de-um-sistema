# 02 — Comandos de terminal (`main.py` na raiz)

**Critério:** 5 — Sistema integrado e dashboard (3 pts) · **Depende de:** [01](01-fase6-deteccao.md) (comando da Fase 6) · **Situação:** ✅ concluída em 08/11/2026

## Objetivo

Um único ponto de entrada no terminal que dispara cada serviço: `python3 main.py <serviço>`. O
enunciado aceita **botão ou comando de terminal**; ter os dois custa pouco e o `main.py` vira a
fonte única de "como rodar cada fase", reaproveitada pela dashboard ([03](03-dashboard-central.md)).

## Serviços

| Comando | O que roda | Testado em 08/11/2026 |
|---|---|---|
| `main.py listar` | Lista os serviços disponíveis | ✅ |
| `main.py fase1` | Programa de terminal de área e insumos (interativo) | ✅ (mesmo programa da Fase 1) |
| `main.py fase1-calculo --cultura manga ...` | Cálculo sem `input()` em `fase1/src/calculo.py`; JSON na saída; `--salvar` grava no CSV | ✅ manga, cana e `--salvar` |
| `main.py fase1-estatistica` | `Rscript Rscripts/python-consumer.r` | ⚠️ R não instalado nesta máquina; a mensagem de aviso foi testada |
| `main.py fase1-clima` | `Rscript Rscripts/weather-getter.r` | ⚠️ idem |
| `main.py fase2-clima` | Código S/L/C da previsão do tempo | ✅ |
| `main.py fase2-regressao` | Regressão logística em R | ⚠️ idem |
| `main.py fase3-consultas` | `fase3/consultas.py` executa `consulta.sql` no Oracle e imprime as 7 tabelas (`--json` opcional) | ✅ 22 linhas em `SENSOR_DADOS` |
| `main.py fase3-dashboard` | Streamlit da Fase 3 na porta 8502 | ✅ |
| `main.py fase4-api` | API da Fase 4 na porta 8000 | ✅ (na 8001, porque a 8000 estava ocupada por outro programa) |
| `main.py fase4-dashboard` | Dashboard central (Fase 4 evoluída) | ✅ sobe a dashboard atual; os botões vêm na [03](03-dashboard-central.md) |
| `main.py fase6 <imagem>` | Detecção com o YOLO | ✅ caminho relativo e absoluto |
| `main.py alerta` | Avalia as últimas leituras e publica os alertas (frente [04](04-alerta-aws.md)) | ⬜ registrado como "em construção"; sai com código 3 |

## Tarefas

- [x] `main.py` só com a biblioteca padrão (`argparse`, `subprocess`, `pathlib`, `shutil`).
- [x] Cada fase roda no seu próprio ambiente com `uv run --project <pasta>` e com a pasta da fase
      como diretório de trabalho (os scripts usam caminhos relativos, como o CSV da Fase 1).
- [x] Mensagens claras quando falta algo: `uv`, `Rscript`, `.env`; dica de conexão com o Oracle
      quando um serviço `fase3-*`/`fase4-*` falha.
- [x] Saída do serviço repassada ao terminal; código de saída devolvido (o `2` da Fase 6, "nada
      detectado", não é tratado como erro).
- [x] Argumentos extras repassados ao serviço, com ou sem `--`. Caminhos relativos que existem a
      partir de onde o usuário está são convertidos para absolutos, porque o serviço roda em outra pasta.
- [x] README da raiz: seção "Disparar os serviços pelo terminal".

## Critério de pronto

- [x] `python3 main.py listar` mostra todos os serviços.
- [x] Os comandos das Fases 1, 2, 3 e 6 rodam a partir da raiz depois de `cp .env.example .env`
      (os de R dependem de ter o R instalado).

## Decisões

- **Fase 1 sem perguntas:** em vez de mexer em `farm_math_handler.py` (que mistura cálculo e
  `input()`), o `calculo.py` reutiliza as funções puras `calculate_mango_area` e
  `calculate_sugar_cane_area` e repete as duas fórmulas de insumo. O programa interativo não mudou.
- **Fase 3 no terminal:** `fase3/consultas.py` usa o ambiente da dashboard (`fase3/dashboard`),
  que já tem `oracledb` e `python-dotenv`; não foi criado outro projeto uv.
- **Portas:** a API fica na 8000 e a dashboard da Fase 3 na 8502, como antes. Se a porta estiver
  ocupada, passe outra (`main.py fase4-api --port 8001`).
