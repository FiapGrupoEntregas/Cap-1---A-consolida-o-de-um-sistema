# 03 — Central de serviços na dashboard (Fase 4 evoluída)

**Critério:** 5 — Sistema integrado e dashboard (3 pts) · **Depende de:** [02](02-cli-main.md) · **Situação:** ✅ concluída em 08/11/2026

## Objetivo

Evoluir a dashboard Streamlit da Fase 4 (`fase4/src/app.py`) para que ela **dispare cada serviço
por um botão**, como pede o enunciado. A análise de solo que já existe continua como uma das páginas.

## Desenho

- Transformar a dashboard em várias páginas (`st.navigation`):
  - **Início:** visão do sistema e estado dos serviços (API no ar, Oracle acessível, AWS configurada);
  - **Análise de solo (Fase 4):** a página atual, sem mudanças de comportamento;
  - **Central de serviços:** um bloco por fase, com botão e resultado na tela.
- Os botões chamam o `main.py` da raiz por `subprocess` e mostram a saída. A lógica de disparo
  fica num só lugar (o `main.py`).
- Serviços que ficam no ar (API da Fase 4, dashboard da Fase 3) sobem em segundo plano, com botão
  de parar e indicação de "no ar".

## Blocos da Central de serviços

| Fase | Interação | Resultado mostrado |
|---|---|---|
| 1 | Formulário (cultura e medidas) + botão "Calcular" | Área e insumo; botão "Estatística em R" mostra a saída do R |
| 2 | Botões "Previsão do tempo" e "Regressão em R"; imagem do circuito | Código S/L/C com a explicação; saída do R e gráfico |
| 3 | Botão "Consultar Oracle"; botão "Abrir dashboard da Fase 3" | Tabelas das consultas; link para a porta 8502 |
| 6 | Envio de imagem + botão "Detectar" | Imagem com as caixas e tabela de classe e confiança |
| Alerta | Botão "Verificar sensores e alertar" | Regras disparadas e confirmação do envio (frente [04](04-alerta-aws.md)) |

## Tarefas

- [x] Fase 1 sem `input()`: feito na frente [02](02-cli-main.md) com `fase1/src/calculo.py`
      (`main.py fase1-calculo`), que devolve JSON. O programa interativo continua funcionando.
- [x] `fase4/src/app.py` reorganizado em páginas (`st.navigation`): `paginas/inicio.py`, `paginas/analise_solo.py`
      (a dashboard original, só com o título ajustado) e `paginas/central.py`.
- [x] Página "Central de serviços" com os blocos acima; `core/servicos.py` faz a ponte com o `main.py`
      (rodar e esperar, ou iniciar/parar em segundo plano com log em `.<serviço>.log`).
- [x] Erros na tela: mensagem com o código de saída e os detalhes (stderr) num expander.
- [ ] Tirar prints de cada bloco funcionando para o README e para o vídeo (fica para a frente [05](05-documentacao-video-entrega.md)).

## Critério de pronto

- [x] Na dashboard, cada uma das Fases 1, 2, 3 e 6 é disparada por um botão e mostra o resultado.
  Testado em 08/11/2026 com o `AppTest` do Streamlit: cálculo da Fase 1, código S/L/C da Fase 2,
  7 consultas da Fase 3, detecção da Fase 6 (vaca_02.jpg) e o aviso do alerta; iniciar/parar da
  dashboard da Fase 3 pela página.
- [x] A análise de solo da Fase 4 continua funcionando como antes (mesmo código, agora em `paginas/analise_solo.py`).

## Decisões

- **Uma única fonte de disparo:** a dashboard não sabe rodar nenhuma fase; ela chama
  `python3 main.py <serviço>` e mostra a saída. Qualquer ajuste de comando é feito só no `main.py`.
- **Serviços em segundo plano:** `Popen` com `start_new_session=True`, para parar o `uv` e o
  processo filho (uvicorn/streamlit) de uma vez com `killpg`. O dicionário de processos fica em
  `st.cache_resource`, compartilhado por todas as sessões da dashboard.
- **Porta já ocupada:** se a porta do serviço responde mas não foi a dashboard que o iniciou, o
  bloco mostra "no ar" com o aviso de que é um processo externo (acontece nesta máquina com a 8000).
- **Fase 5:** continua como notebook; não há botão porque não é um serviço (não é exigido pelo enunciado).
