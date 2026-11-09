# 03 — Central de serviços na dashboard (Fase 4 evoluída)

**Critério:** 5 — Sistema integrado e dashboard (3 pts) · **Depende de:** [02](02-cli-main.md) · **Situação:** ⬜

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

- [ ] Fase 1: separar o cálculo da leitura do teclado em `fase1/src/farm_math_handler.py`
      (funções puras recebendo as medidas) e criar o modo sem `input()` usado por
      `main.py fase1-calculo`. O programa interativo continua funcionando.
- [ ] Reorganizar `fase4/src/app.py` em páginas, sem quebrar a análise de solo.
- [ ] Criar a página "Central de serviços" com os blocos acima.
- [ ] Tratar erros de cada serviço na tela (mensagem amigável em vez de traceback).
- [ ] Tirar prints de cada bloco funcionando para o README e para o vídeo.

## Critério de pronto

- Na dashboard, cada uma das Fases 1, 2, 3 e 6 é disparada por um botão e mostra o resultado.
- A análise de solo da Fase 4 continua funcionando como antes.
