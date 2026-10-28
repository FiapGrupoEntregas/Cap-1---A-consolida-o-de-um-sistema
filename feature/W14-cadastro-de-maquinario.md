# W14 — Cadastro de maquinário e vínculo com o ESP32

| Campo | Valor |
|---|---|
| Prioridade | P1 |
| Camadas | api / front-web |
| Depende de | W1 (catálogo), I3 (persistência), I5 (segurança e auditoria), W5 (painel ao vivo) |
| Janela | 27/09 |
| Responsável | dev-api + dev-front |
| Status | ✅ Concluída |

## Objetivo

Hoje o sistema **só lê**. Fazendas e equipamentos vivem num JSON estático (`api/app/data/farms.json`)
validado no boot, e a única escrita que existe é publicar o limite no MQTT. Falta o registro que a
seguradora precisaria de verdade: **que máquina é essa que está mandando telemetria?**

O `device_id` (`tractor-01`) identifica um **ESP32**, não um trator. Não há onde registrar modelo,
fabricante, ano, horímetro ou histórico de manutenção — nem como dizer que *este* ESP32 está
instalado em *aquela* máquina. Esta feature cria esse cadastro e o vínculo.

Para a banca, ela também fecha uma lacuna óbvia: um sistema de gestão sem nenhuma operação de
escrita pelo usuário é difícil de defender.

## História de usuário

**US-11** em [document/user-stories.md](../document/user-stories.md).

> Como **gestor de frota da fazenda**, quero **cadastrar minhas máquinas e vincular cada uma ao
> dispositivo instalado nela**, para **saber de qual máquina vêm os alertas e manter o registro do
> equipamento junto do seu histórico de risco**.

## Escopo

**Inclui**
- CRUD completo de maquinário: criar, listar, consultar, editar e excluir.
- Vínculo opcional de **um** `device_id` do catálogo (W1) a **uma** máquina.
- Tela de maquinário no front, com formulário de cadastro/edição e confirmação de exclusão.
- Na máquina vinculada, mostrar o estado ao vivo e o histórico do dispositivo, reaproveitando W5/W11.
- Escrita protegida por `X-API-Key` e registrada na trilha de auditoria (I5).

**Não inclui**
- Cadastro de fazendas ou de dispositivos: o catálogo do W1 continua sendo a fonte da verdade e
  segue somente leitura.
- Ordens de serviço, plano de manutenção, custos ou telemetria por máquina no banco.
- Qualquer alteração no firmware ou no contrato MQTT. O ESP32 não sabe que máquinas existem.
- **Qualquer dado pessoal.** Sem nome de operador, CPF, telefone ou matrícula — ver "Regras".

## Regras e lógica

Regra de negócio fica em `api/app/services/machines.py`, com funções puras e testadas. A rota só
traduz para HTTP.

1. **`code` é a identidade humana da máquina** (ex.: `TR-001`). Obrigatório, único,
   1–32 caracteres, normalizado para maiúsculas sem espaços nas pontas. Duplicata → **409**.
2. **`device_id` precisa existir no catálogo** (`farms_service.find_device`). Inexistente → **422**.
3. **Um dispositivo pertence a no máximo uma máquina.** Vincular um `device_id` já usado → **409**
   com a mensagem dizendo qual máquina o tem. O campo é opcional: máquina sem ESP32 é válida.
4. **`farm_id` precisa existir** no catálogo (W1). Inexistente → **422**.
5. **Coerência do vínculo:** se a máquina declara `farm_id` e o dispositivo pertence a outra
   fazenda no catálogo, recusar com **422** — um ESP32 da fazenda A não está instalado numa
   máquina da fazenda B.
6. **`base_tilt_limit_deg` é opcional e informativo.** Quando presente, precisa estar em
   `(0, 90]`. **Não** altera o limite calculado pelo W4: quem manda continua sendo o catálogo e as
   regras (`document/regras-de-risco.md` §4). Isso evita que um cadastro de tela mude, sem revisão,
   o número que vai para o trator.
7. **Excluir a máquina não apaga telemetria nem eventos.** Eles são do dispositivo, não da máquina,
   e continuam no banco. A exclusão só desfaz o vínculo.
8. **LGPD (CLAUDE.md):** o cadastro descreve **bem patrimonial**, nunca pessoa. Os schemas usam
   `extra="forbid"`, então um campo como `operador` é rejeitado na entrada em vez de ser gravado.
   O campo livre `notes` traz aviso na tela para não escrever nome de pessoa.

## Implementação

### API (`api/`)

- **Modelo** — `app/models.py`: tabela `Machine` com `id`, `code` (único, indexado), `name`,
  `type`, `manufacturer`, `model`, `year`, `farm_id`, `device_id` (único, indexado, nulo),
  `base_tilt_limit_deg`, `hour_meter_h`, `acquisition_date`, `notes`, `active`, `created_at`,
  `updated_at`.
- **Repositório** — `app/repositories/machines.py`: consultas e gravação, sem regra de negócio.
- **Serviço** — `app/services/machines.py`: as regras 1–8 acima, como funções puras.
- **Schemas** — `app/schemas/machine.py`: `MachineCreate`, `MachineUpdate` (campos opcionais, com
  distinção entre "não informado" e "limpar"), `MachineResponse`, `MachineWithDevice`.
- **Rotas** — `app/api/v1/routes/machines.py`, prefixo `/api/v1/machines`:

| Método | Caminho | O quê | Chave |
|---|---|---|---|
| `GET` | `/machines` | Lista, com filtros `farm_id`, `type` e `linked` | leitura (W1) |
| `POST` | `/machines` | Cria. **201** com `Location` | ✅ `X-API-Key` |
| `GET` | `/machines/{code}` | Uma máquina, com o dispositivo vinculado e seu estado ao vivo | leitura |
| `PATCH` | `/machines/{code}` | Edição parcial | ✅ `X-API-Key` |
| `DELETE` | `/machines/{code}` | Exclui. **204** | ✅ `X-API-Key` |

- **Auditoria (I5):** `POST`, `PATCH` e `DELETE` gravam em `decision_log` com o `code` afetado e a
  chave mascarada, do mesmo jeito que a publicação de limite já faz.

### Front-web (`front-web/`)

- **Página** `views/machines.py`, registrada na navegação como **"Maquinário"**.
- Lista em tabela com filtro por fazenda e por vínculo, e indicador 🟢/⚫ do dispositivo.
- Formulário de cadastro e edição em `st.form`, com os erros da API exibidos no campo certo.
- Exclusão com confirmação explícita (caixa de digitar o `code`), nunca em um clique só.
- Ao abrir uma máquina vinculada: cartão com estado, última telemetria e histórico, reusando
  `get_device_status` / `get_device_history` do cliente existente.
- Cliente da API em `services/api_client.py`, com `X-API-Key` nas escritas.

### IoT (`iot/`)

Nada. Esta feature não toca o firmware nem o contrato MQTT.

## Critérios de aceite

- [x] 1. Cadastrar uma máquina pela tela e vê-la na lista, com os dados que foram digitados.
- [x] 2. Vincular `tractor-01` a uma máquina; a tela mostra o estado ao vivo e o histórico dele.
- [x] 3. Tentar vincular o mesmo `tractor-01` a uma segunda máquina devolve **409**, e a tela
      explica qual máquina já o utiliza.
- [x] 4. `code` duplicado devolve **409**; `device_id` ou `farm_id` inexistente devolve **422**.
- [x] 5. Editar e excluir funcionam pela tela; a exclusão exige confirmação.
- [x] 6. Sem `X-API-Key`, criar, editar e excluir devolvem **401** e nada muda no banco.
- [x] 7. Excluir uma máquina vinculada **não** apaga a telemetria do dispositivo: o painel ao vivo
      (W5) continua igual.
- [x] 8. O limite publicado no MQTT (W4) é o mesmo antes e depois do cadastro — `base_tilt_limit_deg`
      da máquina não interfere.
- [x] 9. Um `POST` com campo `operador` é rejeitado (**422**) em vez de gravado.
- [x] 10. As três escritas aparecem em `GET /api/v1/audit`.

## Testes

- Serviço: as regras 1–8, uma a uma, com funções puras — incluindo a coerência fazenda × dispositivo.
- Rotas: os dez critérios acima, com banco em memória e sem rede (mockar Open-Meteo e MQTT).
- Regressão: uma máquina vinculada não altera o resultado de `GET /devices/{id}/limit`.
- Front: `tests/test_pages.py` com a API mockada — lista, formulário, erro 409 e confirmação de
  exclusão.

## Riscos e plano B

| Risco | Plano B |
|---|---|
| Cadastro virar fonte de verdade do limite e contradizer o W4 | Regra 6: campo informativo, com teste de regressão (critério 8) |
| Campo livre `notes` receber dado pessoal | `extra="forbid"` nos schemas, aviso na tela e limite de tamanho |
| Escopo crescer para manutenção/ordens de serviço | Fora do escopo declarado; vira item do backlog pós-entrega |
| Mais uma tela para ensaiar antes do vídeo | A tela é autocontida; se o tempo apertar, mostrar só a listagem no vídeo |

## Tarefas

- [x] Modelo, repositório, serviço e schemas na API
- [x] Rotas com chave e auditoria
- [x] Testes de serviço e de rota
- [x] Tela de maquinário e cliente da API
- [x] Testes de front
- [x] README da raiz, `api/README.md`, `front-web/README.md` e `feature/README.md`
- [x] Endpoints em `document/arquitetura.md`
