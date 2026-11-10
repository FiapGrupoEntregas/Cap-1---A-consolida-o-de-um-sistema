# 04 — Serviço de alerta na AWS

**Critério:** 6 — Serviço de alertas na AWS (3 pts) · **Depende de:** leituras em `SOIL_DATA` (Fase 4) · **Situação:** 🟨 código pronto e testado no floci (08/11/2026); falta a AWS real

## Objetivo

Monitorar as leituras dos sensores e, quando algo sair do limite, enviar aos funcionários um
**e-mail** com o problema e a **ação corretiva**, usando o **Amazon SNS**. A parte de nuvem da
Fase 5 não foi entregue, então esta frente também cumpre esse papel.

## O que foi feito (pasta `alerta/`)

| Arquivo | Papel |
|---|---|
| `regras.py` | Funções puras: `avaliar_leitura(leitura)` e `avaliar_deteccao(resumo_yolo)` devolvem os alertas (chave, problema, ação, valor); `montar_mensagem` monta assunto e corpo do e-mail |
| `alerta.py` | O serviço: lê as leituras (Oracle `SOIL_DATA` por padrão, `--fonte api`, `--simular`, `--leitura`), aplica as regras, não repete a mesma condição em menos de 60 min (`.estado.json`), publica no SNS com boto3 e imprime um JSON |
| `floci.py` | `preparar` (tópico + fila SQS assinante + e-mail de exemplo), `ler` (mensagens recebidas na fila), `limpar` |
| `test_regras.py` | 9 testes: cada regra, limites exatos, campos ausentes, vários alertas, regra do YOLO, mensagem |

Também: `main.py alerta` e `main.py alerta-floci`, bloco "Alerta na AWS" na dashboard (escolha
entre as últimas leituras do Oracle ou uma simulação, "Forçar reenvio", tabela de alertas, e-mail
enviado) e as variáveis de AWS no `.env.example`.

### Regras e ações corretivas

| Condição (campo da Fase 4) | Alerta | Ação corretiva |
|---|---|---|
| `soil_moisture_percent` < 60 | Solo seco | Ligar a irrigação do talhão |
| `ph` < 6,0 | Solo ácido | Aplicar calcário (calagem) |
| `ph` > 6,8 | Solo alcalino | Corrigir com enxofre e revisar a adubação |
| `nitrogen`, `phosphorus` ou `potassium` < 30 | Nutriente baixo | Adubar com o nutriente em falta |
| YOLO detecta vaca (`--yolo`) | Animal na lavoura | Verificar as cercas do talhão |

**Decisão (08/11/2026):** N, P e K chegam da Fase 4 como níveis de 0 a 100 % (potenciômetros).
Mínimo adotado: **30 %** para os três (`NUTRIENTE_MINIMO` em `regras.py`). Umidade e pH seguem o
firmware da Fase 2.

### Testado no floci em 08/11/2026

- `docker compose up -d` → floci 2.4.0 com SNS e SQS; `alerta-floci preparar` criou
  `arn:aws:sns:us-east-1:000000000000:farmtech-alertas` com uma fila SQS e um e-mail de exemplo assinando.
- `main.py alerta` com a última leitura real do Oracle (id 211: umidade 50 %, pH 7,0, N 25, P 0, K 0)
  gerou 5 alertas e publicou; `alerta-floci ler` mostrou a mensagem na fila.
- Simulações (`--simular tudo`, `acido`), `--dry-run`, `--forcar`, `--yolo` com o JSON do
  `detect.py` (vaca → "verificar as cercas") e o controle de repetição ("5 repetido(s) dentro do intervalo").
- Botão da dashboard com `AppTest`: simulação `npk` publicada, 2 alertas na tabela.

## O que falta: AWS real (depende da conta do aluno)

Passo a passo para quem tem a conta. Tudo cabe na cota gratuita permanente do SNS (1 milhão de
publicações e 1.000 e-mails por mês), que não depende dos 12 meses de estudante. Reserve uns 30 min.

### Passo 1 — Conta e proteção contra custo

1. Entre em <https://console.aws.amazon.com/> com a conta própria (ou crie uma; pede cartão, mas o uso aqui é zero).
2. **Billing and Cost Management → Budgets → Create budget → Use a template → Zero spend budget**,
   com o seu e-mail. Isso avisa se qualquer centavo for cobrado. **Print 1:** o orçamento criado.
3. Canto superior direito: escolha a região **US East (Ohio) — us-east-2** (a usada na entrega; o `.env` precisa da mesma).

### Passo 2 — Tópico SNS e assinatura de e-mail

1. Procure **Simple Notification Service → Topics → Create topic**.
2. Type **Standard**, Name `farmtech-alertas`, Display name `FarmTech`. Create topic.
   **Print 2:** a página do tópico com o ARN (`arn:aws:sns:us-east-2:<conta>:farmtech-alertas`).
3. No tópico, **Create subscription** → Protocol **Email**, Endpoint: seu e-mail (e o dos colegas,
   um por assinatura). Create subscription.
4. Abra o e-mail "AWS Notification - Subscription Confirmation" e clique em **Confirm subscription**.
   Volte ao console: Status **Confirmed**. **Print 3:** a lista de assinaturas confirmadas.
5. Teste pelo console: **Publish message**, assunto `teste`, corpo `ok`. O e-mail chega em segundos.

### Passo 3 — Usuário IAM só com permissão de publicar

1. **IAM → Policies → Create policy → JSON**, cole (troque `<conta>` pelo número de 12 dígitos do ARN):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": "sns:Publish",
       "Resource": "arn:aws:sns:us-east-2:<conta>:farmtech-alertas"
     }]
   }
   ```
   Nome: `farmtech-sns-publish`. **Print 4:** a política criada.
2. **IAM → Users → Create user**, nome `farmtech-alerta`, sem acesso ao console. Em permissões,
   **Attach policies directly** → `farmtech-sns-publish`. Create user.
3. Abra o usuário → **Security credentials → Create access key → Application running outside AWS**.
   Copie a *Access key* e a *Secret access key* (a secret só aparece uma vez).

### Passo 4 — Apontar o projeto para a AWS

No `.env` da raiz (nunca no Git):

```dotenv
AWS_REGION=us-east-2
SNS_TOPIC_ARN=arn:aws:sns:us-east-2:<conta>:farmtech-alertas
# AWS_ENDPOINT_URL=http://localhost:4566      <- comente esta linha para sair do floci
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

Depois, na raiz:

```bash
python3 main.py alerta --simular seco --forcar      # publica de verdade; o e-mail chega em segundos
python3 main.py alerta --forcar                     # com a última leitura real do Oracle
```

A saída JSON mostra `"destino": "Amazon SNS (us-east-2)"`, `"publicado": true` e o `message_id`.
**Print 5:** o e-mail recebido, com o problema e a ação corretiva. **Print 6 (opcional):**
SNS → tópico → **Monitoring**, gráfico "Number of messages published".

### Passo 5 (recomendado, opcional) — Lambda com as mesmas regras

Mostra o monitoramento rodando *na* AWS, não só a partir do computador.

1. **Lambda → Create function → Author from scratch**, nome `farmtech-alertas`, runtime Python 3.12.
2. No código, substitua todo o `lambda_function.py` pelo arquivo único **`alerta/lambda_function.py`**
   (regras + handler, pronto para colar). Variável de ambiente `SNS_TOPIC_ARN`.
3. **Configuration → Permissions → role** → adicionar a política `farmtech-fase7` (a mesma do usuário IAM,
   ver [cronograma](cronograma-aws.md)).
4. **Test** com um evento como `{"soil_moisture_percent": 35, "ph": 5.2, "nitrogen": 10, "phosphorus": 50, "potassium": 50}`.
   **Print 7:** execução com sucesso e o e-mail recebido.

### Passo 6 — Evidências no repositório

- [ ] Salvar os prints em `docs/imagens/aws/` (`01-orcamento.png`, `02-topico.png`,
      `03-assinaturas.png`, `04-politica-iam.png`, `05-email.png`, `06-monitoring.png`, `07-lambda.png`).
- [ ] No README, seção "Serviço de alertas na AWS": inserir cada print com uma legenda de 1 a 2
      linhas dizendo o que ele mostra e por que importa (tópico criado, assinatura confirmada, menor
      privilégio, e-mail com a ação corretiva).
- [ ] Conferir com `git grep -n AKIA` que nenhuma chave foi parar no repositório.
- [ ] Ao terminar, pode desativar a access key no IAM (o tópico e a assinatura não custam nada).

## Critério de pronto

- [x] Uma leitura fora do limite gera a mensagem com problema e ação corretiva (floci).
- [ ] O mesmo acontece na AWS real e o e-mail chega.
- [ ] Prints do console da AWS comentados no README.
- [x] Nenhuma credencial no repositório (`.env` ignorado; `.env.example` só com exemplos).

## Por que não só o floci

O enunciado pede "serviço de mensageria **na AWS**", "**prints do console da AWS**" e o **envio**
de e-mail ou SMS. O floci não tem console e não entrega e-mail de verdade (ele aceita a assinatura de
e-mail, mas só a fila SQS mostra que a mensagem saiu), então serve para desenvolver e testar, mas não
substitui a AWS na entrega.
