# 04 — Serviço de alerta na AWS

**Critério:** 6 — Serviço de alertas na AWS (3 pts) · **Depende de:** API da Fase 4 no ar · **Situação:** ⬜

## Objetivo

Monitorar as leituras dos sensores e, quando algo sair do limite, enviar aos funcionários um
**e-mail** com o problema e a **ação corretiva**, usando o **Amazon SNS**. A parte de nuvem da
Fase 5 não foi entregue, então esta frente também cumpre esse papel.

## Arquitetura

```
ESP32 (Fase 4) --> API FastAPI --> Oracle SOIL_DATA
                         |
                 regras de alerta (Python, funções puras)
                         |
                  boto3 sns.publish
                         |
        AWS_ENDPOINT_URL definido?  sim --> floci (local, desenvolvimento)
                                    não --> Amazon SNS --> e-mail dos funcionários
```

- **Fonte dos dados:** leituras da Fase 4 (`SOIL_DATA`), pela API (`GET /soil`). Opcional: resultado
  do YOLO ([01](01-fase6-deteccao.md)).
- **Onde as regras rodam:** num módulo Python chamado por `main.py alerta` e pelo botão da
  dashboard. **Melhoria recomendada:** levar as regras para uma **AWS Lambda**, para que o
  monitoramento também rode na nuvem.

## Regras e ações corretivas

Limites de umidade e pH vindos do firmware da Fase 2 (cultura de referência: tomate):

| Condição (campo da Fase 4) | Alerta | Ação corretiva |
|---|---|---|
| `soil_moisture_percent` < 60 | Solo seco | Ligar a irrigação do talhão |
| `ph` < 6,0 | Solo ácido | Aplicar calcário (calagem) |
| `ph` > 6,8 | Solo alcalino | Corrigir com enxofre e revisar a adubação |
| `nitrogen`, `phosphorus` ou `potassium` abaixo do mínimo | Nutriente baixo | Adubar com o nutriente em falta |
| *(opcional)* YOLO detecta vaca | Animal na lavoura | Verificar as cercas do talhão |

**Decisão pendente:** na Fase 4, N, P e K chegam como níveis de **0 a 100%** (potenciômetros), não
como presente/ausente. Definir o nível mínimo de cada um e registrar a escolha aqui antes de codar.

## Tarefas

**Código (desenvolvido no floci)**
- [ ] Módulo de regras com funções puras: recebe uma leitura e devolve a lista de alertas
      (problema e ação). Testes cobrindo cada regra e os limites exatos.
- [ ] Publicador SNS com `boto3`; o destino vem do `.env` (`SNS_TOPIC_ARN`, `AWS_REGION` e,
      no desenvolvimento, `AWS_ENDPOINT_URL=http://localhost:4566`).
- [ ] Mensagem com assunto curto, leitura, problema, ação corretiva e horário.
- [ ] Não repetir o mesmo alerta para a mesma condição em sequência (intervalo mínimo).
- [ ] `main.py alerta` e o botão na dashboard.
- [ ] Testar no floci (`docker compose up -d`): criar o tópico, assinar uma fila SQS e conferir as
      mensagens. O floci não envia e-mail de verdade.

**AWS real (entrega)**
- [ ] Usar uma conta própria. O SNS tem cota gratuita permanente (1 milhão de publicações e 1.000
      e-mails por mês) e o Lambda também (1 milhão de execuções por mês), independente dos 12
      meses de estudante. Confirmar no painel de cobrança.
- [ ] Criar um **alerta de orçamento** de US$ 1 antes de tudo.
- [ ] Criar o tópico `farmtech-alertas` e a assinatura de e-mail; confirmar pelo link recebido.
- [ ] Criar um usuário IAM só com `sns:Publish` nesse tópico (menor privilégio) e pôr as chaves no
      `.env`, nunca no Git.
- [ ] *(Recomendado)* Lambda `farmtech-alertas` com as mesmas regras.
- [ ] Gerar alertas a partir de leituras reais (ESP32 no Wokwi ou `POST /simulate`).

**Evidências**
- [ ] Prints em `docs/imagens/aws/`: tópico, assinatura confirmada, política IAM, Lambda (se
      houver), e-mail recebido, alerta de orçamento.
- [ ] Seção "Serviço de alertas na AWS" do README com os prints comentados.

## Critério de pronto

- Uma leitura fora do limite gera um e-mail real com o problema e a ação corretiva.
- Prints do console da AWS comentados no README.
- Nenhuma credencial no repositório.

## Por que não só o floci

O enunciado pede "serviço de mensageria **na AWS**", "**prints do console da AWS**" e o **envio**
de e-mail ou SMS. O floci não tem console e não entrega e-mail de verdade, então serve para
desenvolver e testar, mas não substitui a AWS na entrega.
