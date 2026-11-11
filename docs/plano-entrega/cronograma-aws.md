# Cronograma: o que falta e depende de você (AWS, prints e vídeos)

Tudo o que o código já faz está pronto e testado no floci. O que resta precisa da **sua conta AWS**
(US$ 100 de créditos) e da sua voz nos vídeos. Está dividido em sessões curtas; faça uma por vez e
marque as caixas. Tempo total estimado: **4 a 5 horas**, com os vídeos.

| Sessão | O quê | Tempo | Custo |
|---|---|---|---|
| [1](#sessão-1--conta-orçamento-e-usuário-iam-30-min) | Conta, orçamento e usuário IAM | 30 min | 0 |
| [2](#sessão-2--sns-e-o-alerta-real-30-min) | Tópico SNS, assinatura e alerta real | 30 min | 0 (cota permanente) |
| [3](#sessão-3--lambda-com-as-regras-45-min) | Lambda com as regras do alerta | 45 min | 0 (cota permanente) |
| [4](#sessão-4--ir-além-1-rekognition-30-min) | Ir Além 1: Rekognition | 30 min | ≈ US$ 0,01 dos créditos |
| [5](#sessão-5--evidências-no-repositório-45-min) | Prints no repositório e legendas no README | 45 min | 0 |
| [6](#sessão-6--vídeos-e-entrega-15-h) | Vídeos (10 min + 2 × 4 min; roteiros em [roteiros-videos.md](roteiros-videos.md)), PR, repositório privado, `.txt` | 1,5 h | 0 |

**Região escolhida: us-east-2 (Ohio).** Onde este arquivo diz `us-east-1`, leia `us-east-2`; o `.env` já está
com `AWS_REGION=us-east-2` e o ARN do tópico em `us-east-2`.

Antes de começar: `git status` limpo ou com as mudanças commitadas, floci parado
(`docker compose down`) para não confundir o destino do alerta.

---

## Sessão 1 — Conta, orçamento e usuário IAM (30 min)

1. [ x] Entre em <https://console.aws.amazon.com/>. Região **US East (N. Virginia) — us-east-1** no canto
       superior direito (a mesma do `.env`).
2. [x ] **Billing and Cost Management → Credits**: confira o saldo e a validade dos US$ 100. Se a conta
       for do nível gratuito novo (criada após jul/2025), algumas ações do roteiro rendem créditos extras
       (criar orçamento, criar Lambda); a própria página diz quais.
3. [ x] **Billing → Budgets → Create budget → Use a template → Monthly cost budget**, valor **US$ 5**,
       seu e-mail. (Não use "Zero spend": ele dispara a cada centavo do Rekognition, mesmo coberto pelos créditos.)
       📸 `docs/imagens/aws/01-orcamento.png`
4. [x] **IAM → Policies → Create policy → JSON**. Esta política cobre as sessões 2 e 4. Troque `<conta>`
       pelo número de 12 dígitos (aparece no canto superior direito, no menu da conta):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       { "Effect": "Allow", "Action": "sns:Publish",
         "Resource": "arn:aws:sns:us-east-1:<conta>:farmtech-alertas" },
       { "Effect": "Allow", "Action": "rekognition:DetectLabels", "Resource": "*" }
     ]
   }
   ```
   Nome: `farmtech-fase7`. 📸 `docs/imagens/aws/02-politica-iam.png` (mostre o JSON).
5. [x] **IAM → Users → Create user** `farmtech-alerta`, **sem** acesso ao console → **Attach policies
       directly** → `farmtech-fase7` → Create user.
6. [x] Abra o usuário → **Security credentials → Create access key → Application running outside AWS**.
       Copie as duas chaves (a secreta só aparece agora). 📸 `docs/imagens/aws/03-usuario-iam.png`
       (a página de permissões do usuário; **nunca** a chave).
7. [x] No `.env` da raiz, edite o bloco da AWS:
   ```dotenv
   AWS_REGION=us-east-1
   SNS_TOPIC_ARN=                        # preenche na sessão 2
   # AWS_ENDPOINT_URL=http://localhost:4566    <- comentado: sai do floci
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   ```

## Sessão 2 — SNS e o alerta real (30 min)

1. [x] **Simple Notification Service → Topics → Create topic**: tipo **Standard**, nome
       `farmtech-alertas`, display name `FarmTech`. 📸 `docs/imagens/aws/04-topico.png` (com o ARN visível).
2. [x] Copie o ARN para `SNS_TOPIC_ARN` no `.env`.
3. [x] No tópico, **Create subscription** → Protocol **Email** → seu e-mail. Repita para cada colega.
4. [x] Abra o e-mail "AWS Notification - Subscription Confirmation" → **Confirm subscription**. No console,
       Status = **Confirmed**. 📸 `docs/imagens/aws/05-assinaturas.png`
5. [x] Teste rápido pelo console: **Publish message** com assunto `teste` → o e-mail chega.
6. [x] No terminal, na raiz do repositório:
   ```bash
   python3 main.py alerta --simular seco --forcar     # deve mostrar "destino": "Amazon SNS (us-east-1)", "publicado": true
   python3 main.py alerta --forcar                    # última leitura real do Oracle
   ```
   📸 `docs/imagens/aws/06-terminal-alerta.png` e 📸 `docs/imagens/aws/07-email.png` (o e-mail com
   problema e ação corretiva).
7. [x] Reinicie a dashboard (`Ctrl+C` e `python3 main.py fase4-dashboard`) para ela ler o novo `.env`.
       Na Central → bloco Alerta → "simular: npk", "Forçar reenvio" → **Verificar sensores e alertar**.
       📸 `docs/imagens/aws/08-dashboard-alerta.png`
8. [x] SNS → tópico → aba **Monitoring**: gráfico "Number of messages published".
       📸 `docs/imagens/aws/09-monitoring.png`

## Sessão 3 — Lambda com as regras (45 min)

Mostra o monitoramento rodando **dentro** da AWS, não só a partir do seu computador. Recomendado.

1. [x] **Lambda → Create function → Author from scratch**: nome `farmtech-alertas`, runtime
       **Python 3.12**, arquitetura x86_64. Create function.
2. [x] Na aba **Code**, apague **todo** o conteúdo de `lambda_function.py` e cole o arquivo
       **`alerta/lambda_function.py`** inteiro (ele já reúne as regras de `regras.py` e o handler; não
       precisa colar duas partes). Clique em **Deploy**. Se aparecer `NameError: name 'avaliar_leitura'
       is not defined`, é porque só o handler foi colado: o arquivo tem ~140 linhas e começa com uma docstring.
3. [x] **Configuration → Environment variables → Edit**: `SNS_TOPIC_ARN` = o ARN do tópico.
4. [x] **Configuration → Permissions → clique na role** → **Add permissions → Attach policies** →
       `farmtech-fase7`. 📸 `docs/imagens/aws/10-lambda-permissoes.png`
5. [x] Aba **Test → Create new event**, nome `solo-seco`, JSON:
   ```json
   {"soil_moisture_percent": 35, "ph": 5.2, "nitrogen": 10, "phosphorus": 50, "potassium": 50}
   ```
   **Test** → "Executing function: succeeded" e o e-mail chega. 📸 `docs/imagens/aws/11-lambda-teste.png`
6. [ ] (Opcional, 10 min) **Add trigger → EventBridge (CloudWatch Events) → Schedule expression**
       `rate(1 hour)` para rodar sozinha. Como a Lambda não acessa o Oracle da FIAP, use-a com o evento de
       teste ou chame-a a partir do `alerta.py` no futuro. Anote no README que é uma melhoria.

## Sessão 4 — Ir Além 1: Rekognition (30 min)

1. [ ] **Rekognition → Label detection** (menu "Demos") → **Upload** `fase6/data/amostras/vaca_02.jpg`.
       Veja **Results** (rótulos e confiança) e **Request / Response** (o JSON).
       📸 `IR-ALEM/ir-alem-1/prints/03-demo-console.png`. Repita com `trator_01.jpg` se quiser um segundo print.
2. [ ] Prints da sessão 1 que também servem aqui: copie `02-politica-iam.png` e `03-usuario-iam.png` para
       `IR-ALEM/ir-alem-1/prints/01-politica-iam.png` e `02-usuario-iam.png`.
3. [x] No terminal (feito em 10/11/2026):
   ```bash
   python3 main.py ir-alem-1 --comparar
   ```
   Gera `IR-ALEM/ir-alem-1/resultados/` (JSON por foto, imagens anotadas, `comparacao.md`).
   📸 `IR-ALEM/ir-alem-1/prints/04-terminal.png`
4. [ ] Abra `resultados/vaca_02_rekognition.jpg` e `fase6/saidas/vaca_02_*.jpg` lado a lado.
       📸 `IR-ALEM/ir-alem-1/prints/05-comparacao.png`
5. [x] `IR-ALEM/README.md` atualizado com os números reais (10/11/2026).
6. [ ] No dia seguinte, **Billing → Bills** mostra a cobrança do Rekognition (centavos, abatidos dos créditos).
       📸 `IR-ALEM/ir-alem-1/prints/06-custo.png`

## Sessão 5 — Evidências no repositório (45 min)

1. [ ] Prints em `docs/imagens/aws/` e `IR-ALEM/ir-alem-1/prints/` com os nomes acima (PNG, recorte só
       a parte relevante, sem o número da conta à mostra se preferir borrar).
2. [ ] README da raiz, seção "Serviço de alertas na AWS": uma legenda de 1 a 2 linhas por print, dizendo
       o que ele mostra e por que importa (tópico criado; assinatura confirmada; menor privilégio no IAM;
       e-mail com a ação corretiva; Lambda executando as regras). Posso escrever essas legendas quando os
       arquivos estiverem na pasta.
3. [ ] Commitar `IR-ALEM/ir-alem-1/resultados/` (resultado real) e os prints.
4. [ ] `git grep -n 'AKIA[0-9A-Z]\{16\}'` deve voltar vazio.
5. [ ] Nomes completos e RMs dos 4 integrantes no README (hoje estão abreviados).

## Sessão 6 — Vídeos e entrega (1,5 h)

1. [ ] **Vídeo principal (≤ 10 min):** roteiro com tempos em
       [05-documentacao-video-entrega.md](05-documentacao-video-entrega.md). Antes de gravar, suba a API
       e a dashboard (`python3 main.py fase4-api` e `python3 main.py fase4-dashboard`) e deixe o e-mail aberto
       para mostrar o alerta chegando.
2. [ ] **Ir Além 2 (≤ 4 min):** abrir o notebook, problema → dados → operadores → figura dos operadores →
       plano final.
3. [ ] **Ir Além 1 (≤ 4 min):** demo do console → `main.py ir-alem-1 --comparar` → comparação com o YOLO.
4. [ ] Publicar os três no YouTube como **não listado** e colocar os links no README e no `.txt`.
5. [ ] Pull request de `feature/entrega-cap-1-fase7` para `main` e merge.
6. [ ] Repositório **privado** (Settings → General → Danger Zone) e `fiap-tutoria` como colaborador.
7. [ ] `.txt` no portal com os links do repositório e dos vídeos. **Nenhum commit depois do envio.**
8. [ ] Depois da entrega: desativar a access key no IAM (Security credentials → Deactivate). Tópico, Lambda
       e assinatura não custam nada parados.
