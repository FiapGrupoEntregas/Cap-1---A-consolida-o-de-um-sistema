# Rodar o AgriShield em Docker

Sobe **API** e **front-web** em containers, sem instalar Python, uv ou dependências na máquina.
O broker MQTT padrão é o **público** (`broker.hivemq.com`), pelo motivo explicado
[abaixo](#o-esp32-e-o-broker-por-que-o-público).

```bash
cp docker/.env.example .env      # escolha uma chave em AGRISHIELD_API_KEY
docker compose up --build
```

| Serviço | Endereço |
|---|---|
| Front-web | http://localhost:8501 |
| API (documentação interativa) | http://localhost:8000/docs |
| Broker MQTT | `broker.hivemq.com:1883` (público; o ESP32 do Wokwi só alcança este) |

Para parar: `Ctrl+C`, ou `docker compose down` noutro terminal.

## ⚠️ O container usa OUTRO banco que a sua máquina

Esta é a pegadinha que mais custa tempo, então vem antes de tudo:

| Onde você roda | Banco usado |
|---|---|
| `uv run ... scripts/load_psr.py` **no host** | `api/agrishield.db` (um arquivo no repositório) |
| A API **em container** | o volume `agrishield-db`, montado em `/data` |

São **arquivos diferentes**. Carregar o PSR no host e depois olhar os relatórios do container
mostra **tudo zerado**, sem nenhum erro na tela — porque o container está lendo um banco vazio.

Se você já tem a base completa carregada no host, leve só a tabela de apólices para o container:

```bash
./scripts/importar-psr-no-docker.sh
```

Ele copia **apenas** a tabela `policy` e **preserva** o que já existe no volume: máquinas
cadastradas, telemetria, eventos e trilha de auditoria.

## Semear a base de sinistros

O banco começa vazio, então os **relatórios por cultura, região e equipamento** (W12) e o
**perfil de subscrição** (W8) vêm sem dados. Para carregar a amostra versionada do PSR
(~450 apólices, suficiente para a demo):

```bash
docker compose run --rm api python scripts/load_psr.py --sample
```

O banco fica num **volume nomeado**, então ele sobrevive a `docker compose down` — semear uma
vez basta. Para zerar de verdade: `docker compose down -v`.

> A base completa (~470 MB de CSV, `load_psr.py` sem `--sample`) **não** é recomendada dentro do
> container: ela gera um banco de ~400 MB. Para isso, rode fora do Docker, como descreve o
> [guia do projeto § 6.5](../document/guia-do-projeto.md#65-a-base-real-do-psr-o-dataset-e-o-modelo).

## Uma chave, duas pontas

O erro mais comum de configuração deste projeto é a chave da API e a chave do front não
combinarem — o sintoma aparece só quando alguém clica em "Enviar ao equipamento" e recebe 401,
normalmente no meio da apresentação. O `scripts/run-demo.sh` existe em parte para avisar disso.

No Docker isso **não pode acontecer**: `AGRISHIELD_API_KEY` do `.env` alimenta as duas pontas
(`AGRISHIELD_API_KEYS` na API e `AGRISHIELD_API_KEY` no front). Há uma fonte só, então elas não
têm como divergir. Sem a variável, o `docker compose up` para com a mensagem dizendo o que falta.

## O ESP32 e o broker: por que o público

Não há container para o dispositivo — ele é **simulado no Wokwi**, e entra na rede
**`Wokwi-GUEST`**. Essa rede é simulada: o tráfego dela sai pela **nuvem da Wokwi**, não pela sua
máquina. Um broker em rede local, inclusive o `mosquitto` deste compose, é **inalcançável de lá**.

Por isso o padrão é `broker.hivemq.com`, e não há o que configurar: `docker compose up` já sobe
pronto para o Wokwi.

> Alcançar um broker local a partir do Wokwi exigiria o **Private Gateway** (plano pago da Wokwi),
> que coloca o dispositivo simulado na sua rede real. O projeto não depende disso.

### Broker local, para trabalho offline

Se você quer desenvolver **sem internet** — usando o simulador de dispositivo no lugar do Wokwi —
há um Mosquitto opcional:

```bash
docker compose --profile broker up -d        # sobe api, front e mosquitto
# no .env:  AGRISHIELD_MQTT_HOST=mosquitto
AGRISHIELD_MQTT_HOST=localhost uv run --project api python scripts/simulate_device.py
```

A porta 1883 é publicada na máquina, então clientes fora da rede do compose falam com ele pelo IP
da LAN — medido em
[evidências § 4b](../document/evidencias/2026-09-27-execucao-em-docker.md). **O Wokwi continua
fora**: neste modo o dispositivo simulado não participa.

O `mosquitto.conf` aceita conexão anônima, o que é defensável em rede local de desenvolvimento e
**não** é ponto de partida para produção — ver o
[contrato MQTT](../document/contrato-mqtt.md#segurança-do-transporte-e-ambientes).

### Se o equipamento aparecer offline

A causa quase sempre é a API e o dispositivo em brokers diferentes, e **nada na tela avisa**:

```bash
uv run --project api python scripts/diagnosticar_mqtt.py
```

## Por que `AGRISHIELD_ENVIRONMENT=dev`

O compose fixa `dev`, e isso é escolha, não descuido. Fora de `dev` a API:

- exige `X-API-Key` também nas **leituras**, e o front só manda chave nas escritas — todas as
  telas quebrariam com 401;
- recusa broker público, que é justamente o que o Wokwi precisa.

`dev` é o modo da demo local. O que produção exigiria está no
[contrato MQTT § Segurança do transporte](../document/contrato-mqtt.md#segurança-do-transporte-e-ambientes)
e no [backlog pós-entrega](../document/backlog-pos-entrega.md).

## Arquivos

| Arquivo | O quê |
|---|---|
| `../docker-compose.yml` | Os três serviços (`api`, `front`, `mosquitto`) e o volume do banco |
| `api.Dockerfile` | Imagem da API. Contexto de build: a **raiz**, porque os scripts de dados e `data/sample/` ficam fora de `api/` |
| `front.Dockerfile` | Imagem do front-web |
| `mosquitto.conf` | Configuração do broker: porta 1883, anônimo e retained persistido |
| `.env.example` | Modelo do `.env` da raiz, lido pelo compose |
| `../.dockerignore` | O que fica fora do contexto. **Não é detalhe:** sem ele o contexto passaria de 1,8 GB (os dois `.venv`, o banco de 399 MB e `data/raw`) |

## Problemas comuns

| Sintoma | Causa |
|---|---|
| `docker compose up` para dizendo "defina AGRISHIELD_API_KEY no .env" | Falta o `.env` na raiz: `cp docker/.env.example .env` |
| **`docker compose down`, `ps` ou `logs` também falham** com a mesma mensagem | Efeito do `${VAR:?}`, que é verificado na interpolação: **qualquer** comando do compose exige a variável. Se você apagou o `.env` com os containers no ar, recrie-o para poder derrubá-los (ou use `docker stop agrishield-api-1 agrishield-front-1`) |
| Relatórios e subscrição vazios | O banco do **container** está vazio — carregar o PSR no host não alimenta o container, são bancos diferentes. Rode `./scripts/importar-psr-no-docker.sh` ou `docker compose run --rm api python scripts/load_psr.py --sample` |
| Aba **Equipamento** zerada, as outras com dados | Ela vem de **telemetria**, não do PSR. Só enche com o ESP32 (ou o simulador) publicando |
| Mapa e previsão respondem 503 | Cota diária da Open-Meteo esgotada; vira às 00:00 UTC (21:00 em Brasília) |
| Porta 8000 ou 8501 ocupada | Já há uma API ou front rodando fora do Docker |
| Telemetria não aparece com o Wokwi **web** | Ele não alcança a sua LAN. Aponte a API para `broker.hivemq.com` no `.env`, ou use o Wokwi no VS Code com Private Gateway. **Para confirmar em 30 s:** `uv run --project api python scripts/diagnosticar_mqtt.py` |
| Telemetria não aparece, e o broker está certo | Confira se o `AGRISHIELD_MQTT_TOPIC_PREFIX` do container e o `TOPIC_PREFIX` do firmware são iguais |
| Equipamento **pisca** entre online e offline a cada ~30 s | A aba do Wokwi está em segundo plano e o navegador a estrangulou; o ping do MQTT não sai. Deixe a aba visível — o Serial deve imprimir ~1 linha por segundo |
| O ESP32 não conecta em `localhost:1883` | `localhost`, para o ESP32 simulado, é **ele mesmo**. Use o IP da máquina na LAN |
