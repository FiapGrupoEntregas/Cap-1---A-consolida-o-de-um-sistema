# I7 — Execução em Docker local

| Campo | Valor |
|---|---|
| Prioridade | P2 |
| Camadas | api / front-web / iot / infra |
| Depende de | I4 (ambiente de demo), I5 (chave de API) |
| Janela | 27/09 |
| Responsável | — |
| Status | ✅ Concluída |

## Objetivo

Rodar a API e o front sem instalar Python, uv ou dependências na máquina. Resolve dois problemas
concretos:

1. **Quem avalia o projeto não precisa montar o ambiente.** Hoje são dois `uv sync`, dois `.env` e
   uma versão de Python compatível. Com Docker é `cp` e `docker compose up`.
2. **Prova que o projeto roda fora da máquina de quem o escreveu.** O ambiente do container é
   limpo, então qualquer dependência não declarada em `requirements.txt` aparece como erro de build
   em vez de funcionar por acidente.

**Não substitui o `run-demo.sh`** (I4), que continua sendo o caminho da apresentação: ele aquece o
cache, confere as chaves e derruba tudo com um Ctrl+C.

## História de usuário

> Como **avaliador (ou pessoa nova no time)**, quero **subir o sistema com um comando**, para
> **ver o produto funcionando sem montar ambiente de desenvolvimento**.

## Escopo

**Inclui**
- `docker-compose.yml` com `api` e `front`, e um Mosquitto local como perfil opcional.
- Um `Dockerfile` por serviço, e `.dockerignore` na raiz.
- Banco em volume nomeado, semeável pela amostra versionada do PSR.
- `.env` único do compose, alimentando as duas pontas da chave de API.

**Não inclui**
- **Container do ESP32.** Ele é simulado no Wokwi; o que a feature faz é deixá-lo **alcançar** o
  broker do compose pelo IP da LAN, não containerizá-lo.
- Imagem de produção: sem TLS no ingresso, sem migrações versionadas, sem backup. Isso é o item 14
  do [backlog pós-entrega](../document/backlog-pos-entrega.md).
- Publicar imagem em registro, orquestração ou deploy em nuvem.
- Alteração de qualquer código de aplicação. A feature é só empacotamento.

## Regras e lógica

1. **O broker padrão é o público** (`broker.hivemq.com`), na API e no firmware. O ESP32 roda
   simulado no Wokwi e entra na rede `Wokwi-GUEST`, que sai pela **nuvem da Wokwi**: broker em
   rede local é inalcançável de lá. O `mosquitto` existe como **perfil opt-in**
   (`--profile broker`), para trabalho offline com o simulador (I6) — e alcançá-lo de fora da
   rede do Docker, pelo IP da LAN, está medido na evidência § 4b.
   Ver [ADR-015](../document/decisoes.md), que registra a decisão **e a sua revisão**.
2. **`AGRISHIELD_ENVIRONMENT=dev` é fixado, de propósito.** Fora de `dev` a API exige `X-API-Key`
   nas leituras — e o front só envia chave nas escritas, então todas as telas responderiam 401 — e
   recusa broker público. `dev` é o modo da demo local.
3. **Uma variável, duas pontas.** `AGRISHIELD_API_KEY` do `.env` alimenta `AGRISHIELD_API_KEYS` na
   API e `AGRISHIELD_API_KEY` no front. Como há uma fonte só, o descasamento que o `run-demo.sh`
   precisa avisar **deixa de ser possível**. Variável ausente para o `up` com mensagem explícita.
4. **O banco não entra na imagem.** Volume nomeado em `/data`, para sobreviver a
   `docker compose down` e para a imagem não carregar os 399 MB do banco de desenvolvimento.
5. **O contexto de build é a raiz**, não `api/`: os scripts de dados e `data/sample/` ficam fora de
   `api/` e são o que semeia o banco do container.
6. **Versões fixas por `==`**, vindas de `requirements.txt` (gerado por
   `scripts/sync-requirements.sh`, sem hashes). O Dockerfile **não** usa `--require-hashes`.

## Implementação

| Arquivo | O quê |
|---|---|
| `docker-compose.yml` | `api` e `front` por padrão; `mosquitto` no perfil `broker`; volume `agrishield-db` |
| `docker/api.Dockerfile` | `python:3.12-slim`, pip a partir de `api/requirements.txt`, usuário sem privilégio, healthcheck em `/api/v1/health` |
| `docker/front.Dockerfile` | idem, healthcheck em `/_stcore/health`, Streamlit em `0.0.0.0` e headless |
| `docker/mosquitto.conf` | broker do compose: porta 1883, anônimo, retained persistido |
| `iot/src/main.ino` | host do broker **fixo** no público; a macro de sobreposição foi removida (ver ADR-015) |
| `docker/.env.example` | modelo do `.env` da raiz |
| `.dockerignore` | mantém o contexto pequeno: sem ele passaria de **1,8 GB** |
| `docker/README.md` | uso, semeadura, o caso do Wokwi e problemas comuns |

## Critérios de aceite

- [x] 1. `cp docker/.env.example .env && docker compose up --build` sobe os dois serviços, e ambos
      ficam **healthy**.
- [x] 2. A API responde em `localhost:8000/api/v1/health` e o front em `localhost:8501`.
- [x] 3. O front alcança a API pelo nome do serviço (`http://api:8000`), sem endereço fixo.
- [x] 4. `docker compose run --rm api python scripts/load_psr.py --sample` semeia o banco, e o
      relatório por cultura passa a responder com dados.
- [x] 5. O banco **sobrevive** a `docker compose down` seguido de `up`.
- [x] 6. Escrita com a chave do `.env` responde 201; sem chave, 401.
- [x] 7. Sem `AGRISHIELD_API_KEY`, o `up` para com mensagem dizendo o que configurar.
- [x] 8. `docker compose up` sobe pronto para o Wokwi: a ponte MQTT da API conecta no broker
      público e assina os três tópicos do contrato.
- [x] 9. `docker compose --profile broker up` sobe o Mosquitto, e um cliente **fora da rede do
      Docker** publica nele pelo IP da LAN com a API recebendo, gravando e servindo o dado.
- [x] 10. `pio run` compila sem nenhuma variável de ambiente ou flag.

## Testes

Esta feature não tem teste automatizado: ela é empacotamento, e a suíte (1007 + 188) roda fora do
container. A verificação é a execução registrada em
[evidências](../document/evidencias/2026-09-27-execucao-em-docker.md), com os nove critérios acima
exercitados contra os containers de verdade.

## Riscos e plano B

| Risco | Plano B |
|---|---|
| Equipamento offline na tela por API e dispositivo em brokers diferentes | **Aconteceu.** Resolvido tornando o público o padrão dos dois lados, e `scripts/diagnosticar_mqtt.py` detecta a divergência em 30 s |
| IP da LAN mudar por DHCP e quebrar um firmware apontado para o endereço antigo | Deixou de existir: o firmware não aponta mais para IP de LAN |
| `.dockerignore` perder uma entrada e o build ficar lento | O arquivo explica o tamanho de cada exclusão, para a próxima pessoa entender o que está em jogo |
| Divergência entre `requirements.txt` e o que o `uv` instala | `scripts/sync-requirements.sh` continua sendo a fonte; o build falha se algo faltar |
| Confundirem isto com imagem de produção | Declarado no escopo, no `docker/README.md` e no item 14 do backlog |
