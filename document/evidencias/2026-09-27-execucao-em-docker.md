# 27/09/2026 — Execução em Docker local (I7)

Os nove critérios da [I7](../../feature/I7-execucao-em-docker.md) exercitados contra os containers,
não contra mock. Ambiente: Docker 29.8.1, Docker Compose 5.5.1.

## 1. Subida

```bash
cp docker/.env.example .env      # AGRISHIELD_API_KEY=chave-docker-local
docker compose up -d --build
```

```
SERVICE   STATUS                    PORTS
api       Up 28 seconds (healthy)   0.0.0.0:8000->8000/tcp
front     Up 22 seconds (healthy)   0.0.0.0:8501->8501/tcp
```

Os dois ficam **healthy** por healthcheck próprio — `/api/v1/health` na API e `/_stcore/health` no
Streamlit. O `front` só inicia depois de a API estar saudável (`condition: service_healthy`), para a
primeira tela não abrir com erro de conexão.

```
$ curl -s localhost:8000/api/v1/health
{"status":"ok","version":"0.1.0","environment":"dev"}

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" localhost:8501/_stcore/health
HTTP 200
```

✅ Critérios 1 e 2.

## 2. Semeadura da base e persistência

```bash
docker compose run --rm api python scripts/load_psr.py --sample
```

O script roda **de dentro do container** (é por isso que o contexto de build é a raiz do
repositório: `scripts/` e `data/sample/` ficam fora de `api/`). Depois dele:

```
$ curl -s localhost:8000/api/v1/reports/crop | ...
  9 culturas no relatório
```

Em seguida, `docker compose down` e `docker compose up -d`:

```
  depois de down/up, máquinas: ['DK-001']
```

O volume nomeado preserva o banco. Semear uma vez basta; `down -v` é o que zera.

✅ Critérios 4 e 5.

## 3. A chave de API, e o descasamento que deixou de existir

```
  POST com a chave certa: 201
  POST sem chave:         401
```

E, de dentro do container do front:

```
  AGRISHIELD_API_URL = http://api:8000
  máquinas vistas pelo front: ['DK-001']
  chave que o front envia é a mesma? True
```

Uma variável do `.env` alimenta as duas pontas, então **não há como a chave da API e a do front
divergirem** — o erro que o `scripts/run-demo.sh` precisa avisar e que aparece só quando alguém
clica em "Enviar ao equipamento". Sem a variável, o `up` para:

```
error while interpolating services.api.environment.AGRISHIELD_API_KEYS: required variable AGRISHIELD_API_KEY is missing a value: defina AGRISHIELD_API_KEY no .env
error while interpolating services.front.environment.AGRISHIELD_API_KEY: required variable AGRISHIELD_API_KEY is missing a value: defina AGRISHIELD_API_KEY no .env
```

A recusa vem do `${VAR:?mensagem}` do compose e acontece na **interpolação**, antes de qualquer
container existir — e cita as duas pontas, deixando claro que a variável serve às duas.

**Efeito colateral medido:** por ser na interpolação, **todo** comando do compose passa a exigir a
variável — `down`, `ps` e `logs` falham igual. Quem apagar o `.env` com os containers no ar precisa
recriá-lo para derrubá-los. É o preço de falhar cedo em vez de subir com chave vazia; está na tabela
de problemas comuns do [docker/README.md](../../docker/README.md).

✅ Critérios 3, 6 e 7.

## 4. Broker local (perfil opcional)

```bash
docker compose --profile broker up -d
```

Ida e volta pelo broker, de dentro do container:

```
$ mosquitto_sub -t "agrishield/#" -C 1 & mosquitto_pub -t "agrishield/teste" -m "ola do compose"
ola do compose
```

E a ponte da API conectando nele (`AGRISHIELD_MQTT_HOST=mosquitto`):

```json
{"level":"INFO","logger":"app.mqtt.bridge","message":"Ponte MQTT iniciada para mosquitto:1883, prefixo 'agrishield/fiap-sompo-2026', keepalive de 15 s."}
{"level":"INFO","logger":"app.mqtt.bridge","message":"Assinado: agrishield/fiap-sompo-2026/devices/+/telemetry"}
{"level":"INFO","logger":"app.mqtt.bridge","message":"Assinado: agrishield/fiap-sompo-2026/devices/+/events"}
{"level":"INFO","logger":"app.mqtt.bridge","message":"Assinado: agrishield/fiap-sompo-2026/devices/+/status"}
```

Os três tópicos do [contrato](../contrato-mqtt.md) assinados.

✅ Critério 8.

> ⚠️ **Nota de 28/09 — a configuração padrão mudou depois deste teste.** O que está medido aqui
> continua verdadeiro: um cliente fora da rede do Docker **usa** o broker do compose pelo IP da LAN.
> O que mudou é o **padrão**: em uso real, ter o `mosquitto` como broker padrão quebrou a demo do
> grupo (API num broker, ESP32 no outro, painel em "offline" sem pista). O padrão voltou a ser o
> broker público, e o `mosquitto` virou perfil opt-in — ver [ADR-015](../decisoes.md). Esta seção
> vale como prova de que o caminho local **funciona**, não como descrição da configuração atual.

## 4b. O ciclo completo com a pilha inteira em Docker

A pergunta que importa para o desenho: **um dispositivo fora da rede do Docker consegue usar o
broker do compose?** Sim, e o caminho inteiro foi exercitado.

O `mosquitto` publica 1883 em `0.0.0.0`, então clientes externos falam com ele pelo **IP da máquina
na LAN** (não pela rede do compose, e não por `localhost` — para um ESP32 simulado, `localhost` é
ele mesmo).

Primeiro, conectividade crua de fora:

```
  192.168.3.152:1883 OK       (wlan0)
  192.168.3.141:1883 OK       (enp0s31f6)
```

Depois o simulador de dispositivo (I6) rodando **no host**, apontado para esse IP:

```bash
AGRISHIELD_MQTT_HOST=192.168.3.152 uv run --project api python scripts/simulate_device.py \
  --scenario normal --count 5
```

```
[sim] telemetria seq=5 roll=4.8° nível=green
[sim] status -> offline (retained)
[sim] fim: 7 publicações (7 válidas, 0 inválidas), 20.1 s
```

E a API, **dentro do container**, recebendo pela rede do compose:

```json
{"logger":"app.mqtt.bridge","message":"Equipamento tractor-02 está online."}
{"logger":"app.mqtt.bridge","message":"Telemetria de tractor-02: seq=1 roll=4.2° limite=10.0° nível=green"}
...
{"logger":"app.mqtt.bridge","message":"Telemetria de tractor-02: seq=5 roll=4.8° limite=10.0° nível=green"}
{"logger":"app.mqtt.bridge","message":"Equipamento tractor-02 está offline."}
```

Servido de volta pela API:

```
  última leitura -> seq 5 | roll 4.8 | nível green
  leituras gravadas: 5
  status (LWT retained): offline | reportado: offline
```

**Dispositivo externo → broker em container → API em container → banco → resposta HTTP.** Sem o
dispositivo entrar na rede do Docker.

### Duas armadilhas medidas no caminho

1. **O IP da LAN é dinâmico.** No meio deste teste o DHCP renovou e a máquina passou de
   `192.168.3.145` para `192.168.3.152`; a conexão anterior começou a devolver
   `[Errno 113] No route to host`. Um firmware compilado com o IP fixo **para de funcionar quando o
   IP muda** — é o preço de apontar para um endereço de LAN, e vale conferir o IP antes de compilar.
2. **`ufw` estava ativo e não bloqueou.** As regras que o Docker cria para porta publicada não
   passam pela cadeia que o `ufw` controla, então a porta ficou acessível na LAN mesmo com firewall
   ligado. Isso é conveniente aqui e é **exatamente o motivo** para o broker anônimo nunca sair de
   rede local: o firewall do host não o protege.

## 5. Nenhum código de aplicação mudou

A feature é empacotamento: `docker-compose.yml`, dois Dockerfiles, `mosquitto.conf`,
`.env.example`, `.dockerignore` e documentação. Nada em `api/app/`, `front-web/` ou `iot/`.

✅ Critério 9.

## O que esta evidência **não** cobre, e a ressalva que importa

- **O Wokwi não foi exercitado por aqui.** O que foi provado é que um cliente MQTT **fora** da rede
  do Docker usa o broker do compose pelo IP da LAN (§ 4b). Se o **Wokwi** consegue fazer isso depende
  de como ele dá rede ao dispositivo simulado:
  - **Wokwi web** (wokwi.com): a rede simulada sai pela **nuvem da Wokwi**, então `192.168.x.x` é
    inalcançável de lá. Para essa via, aponte a API para `broker.hivemq.com` no `.env`.
  - **Wokwi no VS Code com Private Gateway:** o recurso existe justamente para dar rede local ao
    dispositivo simulado, e nesse modo o broker do compose deve ser alcançável. **Não testado
    aqui** — depende de licença e do ensaio do Wokwi (tarefa T6).
- **Fluxo completo Wokwi → broker → API em container → painel: não testado**, por depender do mesmo
  ensaio T6. O equivalente com o simulador está em § 4b e funciona.
- **Não é imagem de produção.** Sem TLS no ingresso, sem migração versionada, sem backup, e com
  `AGRISHIELD_ENVIRONMENT=dev` fixado — que abre as leituras sem chave. O que produção exigiria está
  no item 14 do [backlog pós-entrega](../backlog-pos-entrega.md).
- **A base completa do PSR não foi carregada no container**, só a amostra de ~450 linhas. A carga
  completa gera banco de ~400 MB e deve ser feita fora do Docker.
- **Uma execução, numa máquina Linux.** Não foi testado em macOS nem em Windows/WSL.
