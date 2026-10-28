"""Cliente HTTP da API do AgriShield.

Única porta de acesso à API. Os métodos de `ApiClient` só fazem a chamada e traduzem
as falhas em `ApiError` (mensagem já pronta para a tela); as funções do módulo
(`list_farms`, `get_farm`, `get_terrain`) são as usadas pelas páginas e ficam em cache
com `st.cache_data`. Nenhuma regra de negócio aqui: os números vêm prontos da API.
"""

from typing import Any

import httpx
import streamlit as st

from config import API_KEY, API_URL

# Tempos de cache do front. O relevo é estável (a API também guarda 24 h por fazenda,
# ver document/arquitetura.md); a lista de fazendas é um JSON versionado.
FARMS_TTL_SECONDS = 600  # 10 min
TERRAIN_TTL_SECONDS = 86_400  # 24 h
RISK_TTL_SECONDS = 3_600  # 1 h, o mesmo da previsão do tempo na API
LIMIT_TTL_SECONDS = 3_600  # 1 h: o limite do dia vem da mesma previsão
# O painel ao vivo (W5) recarrega a cada 2 s; o cache curto só evita chamadas repetidas
# dentro do mesmo ciclo, sem deixar a tela atrasada.
LIVE_TTL_SECONDS = 2
# Perfil de subscrição: sai do relevo, que já tem cache de 24 h na API.
UNDERWRITING_TTL_SECONDS = 86_400
# Relatórios do PSR: 1,5 milhão de linhas e dado histórico — cache longo de propósito (W12).
REPORTS_TTL_SECONDS = 86_400
# Relatório do equipamento: a telemetria continua chegando durante a demo.
EQUIPMENT_REPORT_TTL_SECONDS = 60
# Cadastro de maquinário (W14): muda pela própria tela, então o cache é curto e as escritas
# o limpam na hora (`_clear_machines_cache`). Só evita repetir a mesma leitura no rerun.
MACHINES_TTL_SECONDS = 30

# Cabeçalho da chave de API nas escritas protegidas (I5/ADR-013). Só vai nas rotas que exigem.
API_KEY_HEADER = "X-API-Key"

MISSING_API_KEY_MESSAGE = (
    "A API exige uma chave para enviar o limite ao equipamento e o front está sem ela. "
    "Defina `AGRISHIELD_API_KEY` no `.env` do front-web com uma das chaves de "
    "`AGRISHIELD_API_KEYS` da API e reinicie o Streamlit."
)
REJECTED_API_KEY_MESSAGE = (
    "A API recusou a chave configurada em `AGRISHIELD_API_KEY`. Confira se ela é uma das "
    "chaves da lista `AGRISHIELD_API_KEYS` da API (sem espaços sobrando) e reinicie o Streamlit."
)

# Status em que a API diz "seus dados foram recusados" com um texto pronto para a tela (W14):
# 409 é conflito com algo que já existe, 422 é dado incoerente com o catálogo.
REJECTED_DATA_STATUSES = (httpx.codes.CONFLICT, httpx.codes.UNPROCESSABLE_ENTITY)

HTTP_TIMEOUT_SECONDS = 10.0
DEFAULT_FORECAST_DAYS = 7
DEFAULT_RECOMMENDATION_DAYS = 2  # hoje e amanhã
DEFAULT_TREND_DAYS = 7
DEFAULT_HISTORY_DAYS = 7
DEFAULT_WINDOW_MINUTES = 10
DEFAULT_EVENT_LIMIT = 20


class ApiError(Exception):
    """Falha ao falar com a API, com mensagem em português pronta para `st.error`."""


class NotFoundError(ApiError):
    """O recurso pedido não existe (404): fazenda, equipamento ou telemetria ainda sem dados."""


class ApiKeyError(ApiError):
    """A API recusou a chave de escrita (401, I5). A mensagem diz o que configurar."""


class RejectedDataError(ApiError):
    """A API recusou o que o formulário enviou (409 ou 422).

    O texto vem pronto da API — é ela quem sabe que o código já existe ou qual máquina já usa
    aquele ESP32. `fields` traz os campos apontados pela validação do pydantic (422 com lista
    de erros), para a tela mostrar a mensagem ao lado do campo certo; fica vazio quando a API
    responde com um texto único.
    """

    def __init__(self, message: str, status_code: int, fields: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.fields = fields


class ApiClient:
    def __init__(
        self,
        base_url: str = API_URL,
        transport: httpx.BaseTransport | None = None,
        api_key: str = API_KEY,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=f"{base_url}/api/v1", timeout=HTTP_TIMEOUT_SECONDS, transport=transport
        )

    def health(self) -> dict:
        """Status da API (`GET /api/v1/health`)."""
        return self._get("/health")

    def list_farms(self) -> list[dict]:
        """Fazendas de demonstração (`GET /api/v1/farms`) — W1."""
        return self._get("/farms")

    def get_farm(self, farm_id: str) -> dict:
        """Detalhe de uma fazenda (`GET /api/v1/farms/{farm_id}`) — W1."""
        return self._get(f"/farms/{farm_id}")

    def get_terrain(self, farm_id: str) -> dict:
        """Relevo da fazenda (`GET /api/v1/farms/{farm_id}/terrain`) — W2."""
        return self._get(f"/farms/{farm_id}/terrain")

    def get_risk(
        self,
        farm_id: str,
        days: int = DEFAULT_FORECAST_DAYS,
        scenario: str | None = None,
        include_experimental_mlp: bool = False,
    ) -> dict:
        """Previsão de risco (`GET /api/v1/farms/{farm_id}/risk`) — W3.

        Sem cenário o parâmetro `scenario` é omitido: a API recusa um valor vazio. A MLP só é
        solicitada quando o usuário a habilita explicitamente.
        """
        params: dict[str, Any] = {"days": days}
        if scenario:
            params["scenario"] = scenario
        if include_experimental_mlp:
            params["include_experimental_mlp"] = True
        return self._get(f"/farms/{farm_id}/risk", params=params)

    def get_recommendations(
        self,
        farm_id: str,
        days: int = DEFAULT_RECOMMENDATION_DAYS,
        scenario: str | None = None,
    ) -> list[dict]:
        """O que fazer hoje e amanhã (`GET /api/v1/farms/{farm_id}/recommendations`) — W6."""
        params: dict[str, Any] = {"days": days}
        if scenario:
            params["scenario"] = scenario
        return self._get(f"/farms/{farm_id}/recommendations", params=params)

    def get_underwriting(self, farm_id: str) -> dict:
        """Perfil de risco do terreno (`GET /api/v1/farms/{farm_id}/underwriting`) — W8."""
        return self._get(f"/farms/{farm_id}/underwriting")

    # --- relatórios (W12) ---

    def get_equipment_report(self, device_id: str, days: int = DEFAULT_TREND_DAYS) -> dict:
        """Tendência do equipamento (`GET /api/v1/reports/equipment/{device_id}`) — W12."""
        return self._get(f"/reports/equipment/{device_id}", params={"days": days})

    def get_region_report(
        self, state: str, from_year: int | None = None, to_year: int | None = None
    ) -> dict:
        """Sinistros reais do PSR por UF (`GET /api/v1/reports/region`) — W12."""
        return self._get(
            "/reports/region",
            params=_year_params(state=state, from_year=from_year, to_year=to_year),
        )

    def get_crop_report(
        self,
        from_year: int | None = None,
        to_year: int | None = None,
        state: str | None = None,
    ) -> dict:
        """Taxa de sinistro por cultura (`GET /api/v1/reports/crop`) — W12."""
        return self._get(
            "/reports/crop", params=_year_params(state=state, from_year=from_year, to_year=to_year)
        )

    # --- replay de acidentes reais (W9) ---

    def list_replay_cases(self) -> list[dict]:
        """Casos reais curados (`GET /api/v1/replay/cases`) — W9."""
        return self._get("/replay/cases")

    def get_replay_summary(self) -> dict:
        """Placar dos casos de replay (`GET /api/v1/replay/summary`) — W9."""
        return self._get("/replay/summary")

    def run_replay(
        self,
        case_id: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        date: str | None = None,
    ) -> dict:
        """Roda o motor sobre um acidente (`POST /api/v1/replay`) — W9.

        É POST por causa do corpo, mas é **leitura**: não muda nada no servidor e não leva
        chave de API.
        """
        body: dict[str, Any] = {}
        if case_id:
            body["case_id"] = case_id
        if lat is not None:
            body["lat"] = lat
        if lon is not None:
            body["lon"] = lon
        if date:
            body["date"] = date
        return self._post("/replay", json=body)

    def csv_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        """URL absoluta de um CSV da API, para o navegador baixar direto.

        O CSV é gerado pela API (UTF-8 com BOM, `;` e vírgula decimal): o front nunca monta
        arquivo, só aponta o link.
        """
        clean = {key: value for key, value in (params or {}).items() if value is not None}
        return str(httpx.URL(f"{self.base_url}/api/v1{path}", params=clean))

    # --- equipamento: limite do dia (W4) e painel ao vivo (W5) ---

    def get_device_limit(
        self,
        device_id: str,
        date: str | None = None,
        scenario: str | None = None,
    ) -> dict:
        """Limite do dia do equipamento (`GET /api/v1/devices/{device_id}/limit`) — W4."""
        params: dict[str, Any] = {}
        if date:
            params["date"] = date
        if scenario:
            params["scenario"] = scenario
        return self._get(f"/devices/{device_id}/limit", params=params or None)

    def publish_device_limit(
        self,
        device_id: str,
        date: str | None = None,
        scenario: str | None = None,
    ) -> dict:
        """Envia o limite ao equipamento pelo MQTT (`POST .../limit/publish`) — W4.

        A API devolve 503 quando a ponte MQTT está desconectada.
        """
        body: dict[str, Any] = {}
        if date:
            body["date"] = date
        if scenario:
            body["scenario"] = scenario
        return self._post(f"/devices/{device_id}/limit/publish", json=body, authenticated=True)

    def get_device_status(self, device_id: str) -> dict:
        """Online/offline do equipamento (`GET /api/v1/devices/{device_id}/status`) — W5."""
        return self._get(f"/devices/{device_id}/status")

    def get_latest_telemetry(self, device_id: str) -> dict:
        """Última leitura (`GET .../telemetry/latest`) — W5. 404 enquanto não houver dados."""
        return self._get(f"/devices/{device_id}/telemetry/latest")

    def get_telemetry_series(self, device_id: str, minutes: int = DEFAULT_WINDOW_MINUTES) -> dict:
        """Série dos últimos minutos (`GET .../telemetry?minutes=`) — W5."""
        return self._get(f"/devices/{device_id}/telemetry", params={"minutes": minutes})

    def get_device_history(self, device_id: str, days: int = DEFAULT_HISTORY_DAYS) -> dict:
        """Histórico do equipamento (`GET /api/v1/devices/{device_id}/history`) — W11."""
        return self._get(f"/devices/{device_id}/history", params={"days": days})

    def get_device_events(self, device_id: str, limit: int = DEFAULT_EVENT_LIMIT) -> list[dict]:
        """Eventos do equipamento, do mais recente para o mais antigo (`GET .../events`) — W5."""
        return self._get(f"/devices/{device_id}/events", params={"limit": limit})

    # --- cadastro de maquinário (W14) ---

    def list_machines(
        self,
        farm_id: str | None = None,
        machine_type: str | None = None,
        linked: bool | None = None,
    ) -> list[dict]:
        """Máquinas cadastradas (`GET /api/v1/machines`) — W14.

        Os filtros vazios são omitidos; `linked` é `true`/`false` e nunca `None` na query.
        """
        params: dict[str, Any] = {}
        if farm_id:
            params["farm_id"] = farm_id
        if machine_type:
            params["type"] = machine_type
        if linked is not None:
            params["linked"] = linked
        return self._get("/machines", params=params or None)

    def get_machine(self, code: str) -> dict:
        """Uma máquina com o ESP32 vinculado e o estado ao vivo dele (`GET .../{code}`) — W14.

        A API normaliza o código no caminho: `tr-001` encontra `TR-001`.
        """
        return self._get(f"/machines/{code}")

    def create_machine(self, machine: dict[str, Any]) -> dict:
        """Cadastra uma máquina (`POST /api/v1/machines`, 201) — W14. **Escrita:** leva a chave."""
        return self._post("/machines", json=machine, authenticated=True)

    def update_machine(self, code: str, changes: dict[str, Any]) -> dict:
        """Edição parcial (`PATCH /api/v1/machines/{code}`) — W14. **Escrita:** leva a chave.

        Manda **só** o que mudou: campo ausente do JSON não altera nada e campo presente com
        `None` apaga o valor — é assim que a tela desvincula um ESP32 (`{'device_id': None}`).
        """
        return self._request("PATCH", f"/machines/{code}", json=changes, authenticated=True)

    def delete_machine(self, code: str) -> None:
        """Exclui a máquina (`DELETE /api/v1/machines/{code}`, 204) — W14. **Escrita.**

        A telemetria e os eventos do dispositivo continuam no banco: são dele, não da máquina.
        """
        self._request("DELETE", f"/machines/{code}", authenticated=True)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(
        self, path: str, json: dict[str, Any] | None = None, authenticated: bool = False
    ) -> Any:
        return self._request("POST", path, json=json, authenticated=authenticated)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> Any:
        # A chave só acompanha as rotas protegidas (I5): leitura não leva segredo.
        headers = {API_KEY_HEADER: self.api_key} if authenticated and self.api_key else None
        try:
            response = self._client.request(method, path, params=params, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise ApiError(
                f"Não foi possível falar com a API em {self.base_url}. "
                "Suba a API com `uv run fastapi dev app/main.py` na pasta api/ "
                "ou ajuste a variável AGRISHIELD_API_URL."
            ) from exc

        if response.status_code == httpx.codes.UNAUTHORIZED:
            raise ApiKeyError(REJECTED_API_KEY_MESSAGE if self.api_key else MISSING_API_KEY_MESSAGE)
        if response.status_code == httpx.codes.NOT_FOUND:
            raise NotFoundError(_detail(response, "Recurso não encontrado na API."))
        if response.status_code in REJECTED_DATA_STATUSES:
            # A API já explica o motivo em português (código repetido, ESP32 de outra máquina,
            # fazenda inexistente): a tela mostra esse texto, não um genérico.
            raise RejectedDataError(
                _detail(response, "A API recusou os dados enviados."),
                status_code=response.status_code,
                fields=_error_fields(response),
            )
        if response.is_error:
            raise ApiError(
                _detail(response, "A API respondeu com erro.")
                + f" (HTTP {response.status_code} em {path})"
            )

        # 204 (DELETE) e qualquer resposta sem corpo não têm JSON para ler.
        if response.status_code == httpx.codes.NO_CONTENT or not response.content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(f"A API devolveu uma resposta ilegível em {path}.") from exc


def _year_params(state: str | None, from_year: int | None, to_year: int | None) -> dict[str, Any]:
    """Monta os filtros dos relatórios, omitindo o que está vazio."""
    params: dict[str, Any] = {}
    if state:
        params["state"] = state
    if from_year is not None:
        params["from_year"] = from_year
    if to_year is not None:
        params["to_year"] = to_year
    return params


def _detail(response: httpx.Response, fallback: str) -> str:
    """Mensagem de erro da API (campo `detail` do FastAPI), ou um texto padrão.

    O `detail` vem como **texto** nas regras de negócio (`HTTPException`) e como **lista de
    erros** na validação do pydantic (422 de schema). Os dois viram uma frase só.
    """
    detail = _detail_field(response)
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list):
        messages = [line for line in (_validation_line(item) for item in detail) if line]
        if messages:
            return " · ".join(messages)
    return fallback


def _detail_field(response: httpx.Response) -> Any:
    """O `detail` cru da resposta, ou `None` quando o corpo não é um JSON de erro do FastAPI."""
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload.get("detail") if isinstance(payload, dict) else None


def _validation_line(item: Any) -> str:
    """Um erro de validação do pydantic como 'campo `notes`: mensagem'."""
    if not isinstance(item, dict):
        return ""
    message = item.get("msg") or ""
    field = _field_name(item)
    return f"campo `{field}`: {message}" if field and message else str(message)


def _field_name(item: Any) -> str:
    """Nome do campo apontado por um erro de validação (último item de `loc`)."""
    if not isinstance(item, dict):
        return ""
    location = item.get("loc")
    if not isinstance(location, list) or not location:
        return ""
    last = location[-1]
    return last if isinstance(last, str) and last != "body" else ""


def _error_fields(response: httpx.Response) -> tuple[str, ...]:
    """Campos citados pela validação do pydantic, na ordem, sem repetir."""
    detail = _detail_field(response)
    if not isinstance(detail, list):
        return ()
    names = [_field_name(item) for item in detail]
    return tuple(dict.fromkeys(name for name in names if name))


@st.cache_resource
def get_api() -> ApiClient:
    return ApiClient()


@st.cache_data(ttl=FARMS_TTL_SECONDS, show_spinner=False)
def list_farms() -> list[dict]:
    """Lista de fazendas para o seletor (cache de 10 min)."""
    return get_api().list_farms()


@st.cache_data(ttl=FARMS_TTL_SECONDS, show_spinner=False)
def get_farm(farm_id: str) -> dict:
    """Detalhe da fazenda escolhida (cache de 10 min)."""
    return get_api().get_farm(farm_id)


@st.cache_data(ttl=TERRAIN_TTL_SECONDS, show_spinner="Carregando o relevo da fazenda…")
def get_terrain(farm_id: str) -> dict:
    """Grade de relevo da fazenda (cache de 24 h)."""
    return get_api().get_terrain(farm_id)


@st.cache_data(ttl=RISK_TTL_SECONDS, show_spinner="Calculando o risco dos próximos dias…")
def get_risk(
    farm_id: str,
    days: int = DEFAULT_FORECAST_DAYS,
    scenario: str | None = None,
    include_experimental_mlp: bool = False,
) -> dict:
    """Previsão e, opcionalmente, MLP experimental (cache separado por opção)."""
    return get_api().get_risk(
        farm_id,
        days=days,
        scenario=scenario,
        include_experimental_mlp=include_experimental_mlp,
    )


@st.cache_data(ttl=LIMIT_TTL_SECONDS, show_spinner=False)
def get_device_limit(device_id: str, date: str | None = None, scenario: str | None = None) -> dict:
    """Limite do dia do equipamento (cache de 1 h por equipamento, dia e cenário)."""
    return get_api().get_device_limit(device_id, date=date, scenario=scenario)


def publish_device_limit(
    device_id: str, date: str | None = None, scenario: str | None = None
) -> dict:
    """Envia o limite ao equipamento. **Escrita: nunca entra em cache.**"""
    return get_api().publish_device_limit(device_id, date=date, scenario=scenario)


@st.cache_data(ttl=LIVE_TTL_SECONDS, show_spinner=False)
def get_device_status(device_id: str) -> dict:
    """Estado da conexão do equipamento (cache de 2 s, o ritmo do painel ao vivo)."""
    return get_api().get_device_status(device_id)


@st.cache_data(ttl=LIVE_TTL_SECONDS, show_spinner=False)
def get_latest_telemetry(device_id: str) -> dict:
    """Última leitura do equipamento (cache de 2 s). Levanta `NotFoundError` sem telemetria."""
    return get_api().get_latest_telemetry(device_id)


@st.cache_data(ttl=LIVE_TTL_SECONDS, show_spinner=False)
def get_telemetry_series(device_id: str, minutes: int = DEFAULT_WINDOW_MINUTES) -> dict:
    """Série de roll e pitch dos últimos minutos (cache de 2 s)."""
    return get_api().get_telemetry_series(device_id, minutes=minutes)


@st.cache_data(ttl=LIVE_TTL_SECONDS, show_spinner=False)
def get_device_events(device_id: str, limit: int = DEFAULT_EVENT_LIMIT) -> list[dict]:
    """Eventos do equipamento, do mais recente para o mais antigo (cache de 2 s)."""
    return get_api().get_device_events(device_id, limit=limit)


@st.cache_data(ttl=RISK_TTL_SECONDS, show_spinner=False)
def get_recommendations(
    farm_id: str,
    days: int = DEFAULT_RECOMMENDATION_DAYS,
    scenario: str | None = None,
) -> list[dict]:
    """Janelas seguras e orientações do dia (cache de 1 h por fazenda, dias e cenário)."""
    return get_api().get_recommendations(farm_id, days=days, scenario=scenario)


@st.cache_data(ttl=UNDERWRITING_TTL_SECONDS, show_spinner=False)
def get_underwriting(farm_id: str) -> dict:
    """Perfil de subscrição da fazenda (cache de 24 h)."""
    return get_api().get_underwriting(farm_id)


@st.cache_data(ttl=EQUIPMENT_REPORT_TTL_SECONDS, show_spinner=False)
def get_equipment_report(device_id: str, days: int = DEFAULT_TREND_DAYS) -> dict:
    """Tendência do equipamento (cache de 1 min: a telemetria segue chegando)."""
    return get_api().get_equipment_report(device_id, days=days)


@st.cache_data(ttl=REPORTS_TTL_SECONDS, show_spinner="Consultando os sinistros reais do PSR…")
def get_region_report(state: str, from_year: int | None = None, to_year: int | None = None) -> dict:
    """Relatório de região (cache de 24 h: são 1,5 milhão de apólices por consulta)."""
    return get_api().get_region_report(state, from_year=from_year, to_year=to_year)


@st.cache_data(ttl=REPORTS_TTL_SECONDS, show_spinner="Consultando os sinistros reais do PSR…")
def get_crop_report(
    from_year: int | None = None, to_year: int | None = None, state: str | None = None
) -> dict:
    """Relatório por cultura (cache de 24 h)."""
    return get_api().get_crop_report(from_year=from_year, to_year=to_year, state=state)


def report_csv_url(path: str, params: dict[str, Any] | None = None) -> str:
    """Link de download do CSV que a **API** gera (W12). Não é uma requisição."""
    return get_api().csv_url(path, params)


@st.cache_data(ttl=FARMS_TTL_SECONDS, show_spinner=False)
def list_replay_cases() -> list[dict]:
    """Casos reais de replay (cache de 10 min: é um JSON versionado)."""
    return get_api().list_replay_cases()


@st.cache_data(ttl=REPORTS_TTL_SECONDS, show_spinner="Rodando o motor sobre o dia do acidente…")
def run_replay(
    case_id: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    date: str | None = None,
) -> dict:
    """Replay de um acidente (cache de 24 h).

    O passado não muda e cada consulta bate na Open-Meteo, então o cache é longo de propósito.
    """
    return get_api().run_replay(case_id=case_id, lat=lat, lon=lon, date=date)


@st.cache_data(ttl=REPORTS_TTL_SECONDS, show_spinner="Rodando o motor nos casos reais…")
def get_replay_summary() -> dict:
    """Placar dos casos de replay (cache de 24 h: roda o motor em todos os casos)."""
    return get_api().get_replay_summary()


@st.cache_data(ttl=EQUIPMENT_REPORT_TTL_SECONDS, show_spinner=False)
def get_device_history(device_id: str, days: int = DEFAULT_HISTORY_DAYS) -> dict:
    """Histórico do equipamento (cache de 1 min, como o relatório: a telemetria segue chegando)."""
    return get_api().get_device_history(device_id, days=days)


# --- cadastro de maquinário (W14) ---


@st.cache_data(ttl=MACHINES_TTL_SECONDS, show_spinner=False)
def list_machines(
    farm_id: str | None = None,
    machine_type: str | None = None,
    linked: bool | None = None,
) -> list[dict]:
    """Máquinas cadastradas, já filtradas pela API (cache de 30 s por combinação de filtros)."""
    return get_api().list_machines(farm_id=farm_id, machine_type=machine_type, linked=linked)


@st.cache_data(ttl=MACHINES_TTL_SECONDS, show_spinner=False)
def get_machine(code: str) -> dict:
    """Uma máquina com o ESP32 vinculado e o estado ao vivo dele (cache de 30 s)."""
    return get_api().get_machine(code)


def create_machine(machine: dict[str, Any]) -> dict:
    """Cadastra uma máquina. **Escrita: nunca entra em cache** — e limpa o que já estava lá."""
    created = get_api().create_machine(machine)
    clear_machines_cache()
    return created


def update_machine(code: str, changes: dict[str, Any]) -> dict:
    """Edição parcial da máquina. **Escrita: nunca entra em cache.**"""
    updated = get_api().update_machine(code, changes)
    clear_machines_cache()
    return updated


def delete_machine(code: str) -> None:
    """Exclui a máquina. **Escrita: nunca entra em cache.**"""
    get_api().delete_machine(code)
    clear_machines_cache()


def clear_machines_cache() -> None:
    """Esquece as leituras do cadastro depois de uma escrita, para a lista não mostrar o antigo."""
    list_machines.clear()
    get_machine.clear()
