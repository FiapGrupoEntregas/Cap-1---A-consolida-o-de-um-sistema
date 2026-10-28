"""Testes das rotas do cadastro de maquinário (W14). Sem rede e sem broker.

Um teste por critério de aceite da feature, com banco em memória, Open-Meteo mockada pelas
fixtures do I1/W2 e a ponte MQTT trocada por um dublê. As regras em si estão em
`tests/test_machines.py`.
"""

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.clients.open_meteo import OpenMeteoClient, get_open_meteo_client
from app.core.clock import today_local
from app.core.config import Settings, get_settings
from app.db import get_session
from app.main import app
from app.models import Machine, Telemetry
from app.mqtt.bridge import get_mqtt
from app.repositories import devices as devices_repository
from app.schemas.mqtt import TelemetryMessage
from app.services.terrain import clear_terrain_cache
from tests.conftest import FIXTURES_DIR
from tests.test_devices_limit_route import FakeBridge
from tests.test_risk_route import forecast_payload

FARM_ID = "cafe-carmo-de-minas"
OTHER_FARM_ID = "graos-sorriso"
DEVICE_ID = "tractor-01"

MACHINES_URL = "/api/v1/machines"
AUDIT_URL = "/api/v1/audit"
LIMIT_URL = f"/api/v1/devices/{DEVICE_ID}/limit"
PUBLISH_URL = f"{LIMIT_URL}/publish"

API_KEY = "chave-de-teste-1234"
AUTH = {"X-API-Key": API_KEY}

TRACTOR = {
    "code": "TR-001",
    "name": "Trator cafeeiro",
    "type": "tractor",
    "manufacturer": "John Deere",
    "model": "5075E",
    "year": 2019,
    "farm_id": FARM_ID,
    "hour_meter_h": 3120.5,
    "acquisition_date": "2020-03-15",
    "notes": "Revisão feita na última safra.",
}


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def bridge() -> FakeBridge:
    return FakeBridge()


@pytest.fixture(autouse=True)
def clean_state() -> Iterator[None]:
    clear_terrain_cache()
    yield
    clear_terrain_cache()
    app.dependency_overrides.clear()


@pytest.fixture
def client(
    make_client: Callable[..., OpenMeteoClient], session: Session, bridge: FakeBridge
) -> TestClient:
    """`TestClient` com banco em memória, Open-Meteo mockada e ponte MQTT falsa."""
    today = today_local()

    def handler(request: httpx.Request) -> httpx.Response:
        if "elevation" in request.url.path:
            path = FIXTURES_DIR / "terrain_elevation_carmo.json"
            return httpx.Response(200, json=json.loads(path.read_text(encoding="utf-8")))
        return httpx.Response(200, json=forecast_payload(today))

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_open_meteo_client] = lambda: make_client(handler)
    app.dependency_overrides[get_mqtt] = lambda: bridge
    app.dependency_overrides[get_settings] = lambda: Settings(environment="dev", api_keys=API_KEY)
    return TestClient(app)


def create(client: TestClient, **overrides: object) -> httpx.Response:
    """Cadastra uma máquina, com o que o teste quiser trocar no corpo padrão."""
    return client.post(MACHINES_URL, headers=AUTH, json={**TRACTOR, **overrides})


def save_telemetry(session: Session, device_id: str = DEVICE_ID, seq: int = 1) -> None:
    """Uma leitura recente do equipamento, como a ponte MQTT (I3) gravaria."""
    devices_repository.save_telemetry(
        session,
        TelemetryMessage(
            device_id=device_id,
            ts=0,
            seq=seq,
            roll_deg=6.0,
            pitch_deg=2.0,
            accel_g=1.0,
            tilt_limit_deg=10.0,
            alert_level="green",
        ),
    )


# --- Critério 1: cadastrar e ver na lista --------------------------------------------------------


def test_creating_returns_201_with_location_and_the_typed_data(client: TestClient) -> None:
    response = create(client)

    assert response.status_code == 201
    assert response.headers["Location"].endswith("/api/v1/machines/TR-001")
    body = response.json()
    assert {key: body[key] for key in TRACTOR} == TRACTOR
    assert body["active"] is True
    assert body["device"] is None


def test_the_created_machine_shows_up_in_the_listing(client: TestClient) -> None:
    create(client)

    listed = client.get(MACHINES_URL).json()

    assert [row["code"] for row in listed] == ["TR-001"]
    assert listed[0]["manufacturer"] == "John Deere"
    assert listed[0]["hour_meter_h"] == 3120.5


def test_the_code_is_stored_in_upper_case_and_found_either_way(client: TestClient) -> None:
    assert create(client, code=" tr-001 ").json()["code"] == "TR-001"

    assert client.get(f"{MACHINES_URL}/tr-001").status_code == 200
    assert client.get(f"{MACHINES_URL}/TR-001").status_code == 200


def test_the_listing_filters_by_farm_type_and_link(client: TestClient) -> None:
    create(client, code="TR-001", device_id=DEVICE_ID)
    create(client, code="CO-001", type="harvester", farm_id=OTHER_FARM_ID)

    def codes(params: dict) -> list[str]:
        return [row["code"] for row in client.get(MACHINES_URL, params=params).json()]

    assert codes({}) == ["CO-001", "TR-001"]
    assert codes({"farm_id": FARM_ID}) == ["TR-001"]
    assert codes({"type": "harvester"}) == ["CO-001"]
    assert codes({"linked": "true"}) == ["TR-001"]
    assert codes({"linked": "false"}) == ["CO-001"]


def test_a_blank_filter_means_no_filter(client: TestClient) -> None:
    """`""` é "todas", não "as que têm o campo vazio".

    O `selectbox` do Streamlit devolve string vazia para a opção "todas". Se isso virasse filtro,
    a tela mostraria "nenhuma máquina" com o banco cheio — e só na demo alguém perceberia.
    """
    create(client, code="TR-001", device_id=DEVICE_ID)
    create(client, code="CO-001", type="harvester", farm_id=OTHER_FARM_ID)

    def codes(params: dict) -> list[str]:
        return [row["code"] for row in client.get(MACHINES_URL, params=params).json()]

    assert codes({"type": ""}) == ["CO-001", "TR-001"]
    assert codes({"farm_id": ""}) == ["CO-001", "TR-001"]
    assert codes({"farm_id": "   ", "type": "  "}) == ["CO-001", "TR-001"]


def test_an_unknown_machine_returns_404(client: TestClient) -> None:
    response = client.get(f"{MACHINES_URL}/TR-999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Máquina não encontrada"


# --- Critério 2: vincular o ESP32 e ver o estado ao vivo -----------------------------------------


def test_a_linked_machine_shows_the_catalog_device_and_its_live_state(
    client: TestClient, session: Session
) -> None:
    save_telemetry(session)

    body = create(client, device_id=DEVICE_ID).json()

    assert body["device_id"] == DEVICE_ID
    assert body["device"]["device"]["name"] == "Trator cafeeiro 01"
    assert body["device"]["farm_id"] == FARM_ID
    assert body["device"]["status"]["state"] == "online"
    assert body["device"]["status"]["seconds_since_last_telemetry"] is not None


def test_a_silent_device_appears_offline(client: TestClient) -> None:
    """Sem nenhuma telemetria, o vínculo existe mas o equipamento está offline (W5)."""
    body = create(client, device_id=DEVICE_ID).json()

    assert body["device"]["status"]["state"] == "offline"
    assert body["device"]["status"]["last_seen_at"] is None


def test_the_linked_device_keeps_the_catalog_reference_limit(client: TestClient) -> None:
    """O `L_ref` que vale é o do catálogo, mesmo com outro número no cadastro (regra 6)."""
    body = create(client, device_id=DEVICE_ID, base_tilt_limit_deg=5.0).json()

    assert body["base_tilt_limit_deg"] == 5.0
    assert body["device"]["device"]["base_tilt_limit_deg"] == 15.0


# --- Critério 3: um dispositivo pertence a uma máquina só ----------------------------------------


def test_linking_a_device_that_is_taken_returns_409_naming_the_machine(
    client: TestClient,
) -> None:
    create(client, code="TR-001", device_id=DEVICE_ID)

    response = create(client, code="TR-002", device_id=DEVICE_ID)

    assert response.status_code == 409
    assert "TR-001" in response.json()["detail"]
    assert DEVICE_ID in response.json()["detail"]


def test_unlinking_releases_the_device(client: TestClient) -> None:
    create(client, code="TR-001", device_id=DEVICE_ID)

    unlinked = client.patch(f"{MACHINES_URL}/TR-001", headers=AUTH, json={"device_id": None}).json()
    reused = create(client, code="TR-002", device_id=DEVICE_ID)

    assert unlinked["device_id"] is None
    assert unlinked["device"] is None
    assert reused.status_code == 201


def test_keeping_the_same_device_on_a_patch_is_not_a_conflict(client: TestClient) -> None:
    """A própria máquina não pode se acusar de já usar o dispositivo dela."""
    create(client, code="TR-001", device_id=DEVICE_ID)

    response = client.patch(
        f"{MACHINES_URL}/TR-001", headers=AUTH, json={"name": "Trator cafeeiro (revisado)"}
    )

    assert response.status_code == 200
    assert response.json()["device_id"] == DEVICE_ID


# --- Critério 4: código duplicado, fazenda e dispositivo inexistentes ----------------------------


def test_a_duplicate_code_returns_409(client: TestClient) -> None:
    create(client)

    response = create(client, name="Outro trator")

    assert response.status_code == 409
    assert "TR-001" in response.json()["detail"]


def test_an_unknown_device_returns_422(client: TestClient) -> None:
    response = create(client, device_id="trator-fantasma")

    assert response.status_code == 422
    assert "trator-fantasma" in response.json()["detail"]


def test_an_unknown_farm_returns_422(client: TestClient) -> None:
    response = create(client, farm_id="fazenda-fantasma")

    assert response.status_code == 422
    assert "fazenda-fantasma" in response.json()["detail"]


def test_a_device_from_another_farm_returns_422(client: TestClient) -> None:
    """Regra 5: o ESP32 do café não está instalado numa máquina da fazenda de grãos."""
    response = create(client, farm_id=OTHER_FARM_ID, device_id=DEVICE_ID)

    assert response.status_code == 422
    assert response.json()["detail"].count("fazenda") >= 1
    assert OTHER_FARM_ID in response.json()["detail"]


def test_nothing_is_stored_when_a_rule_refuses(client: TestClient, session: Session) -> None:
    create(client, device_id="trator-fantasma")

    assert session.exec(select(Machine)).all() == []


# --- Critério 5: editar e excluir ----------------------------------------------------------------


def test_a_patch_changes_only_what_came(client: TestClient) -> None:
    created = create(client).json()

    edited = client.patch(
        f"{MACHINES_URL}/TR-001", headers=AUTH, json={"hour_meter_h": 3200.0}
    ).json()

    assert edited["hour_meter_h"] == 3200.0
    assert edited["manufacturer"] == created["manufacturer"]
    assert edited["notes"] == created["notes"]
    assert edited["updated_at"] >= created["updated_at"]


def test_a_patch_with_an_explicit_null_clears_the_field(client: TestClient) -> None:
    create(client)

    edited = client.patch(f"{MACHINES_URL}/TR-001", headers=AUTH, json={"notes": None}).json()

    assert edited["notes"] is None


@pytest.mark.parametrize("field", ["code", "name", "type", "active"])
def test_a_patch_cannot_clear_an_identity_field(client: TestClient, field: str) -> None:
    create(client)

    response = client.patch(f"{MACHINES_URL}/TR-001", headers=AUTH, json={field: None})

    assert response.status_code == 422


def test_deleting_returns_204_and_removes_the_machine(client: TestClient) -> None:
    create(client)

    response = client.delete(f"{MACHINES_URL}/TR-001", headers=AUTH)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"{MACHINES_URL}/TR-001").status_code == 404
    assert client.get(MACHINES_URL).json() == []


def test_deleting_an_unknown_machine_returns_404(client: TestClient) -> None:
    assert client.delete(f"{MACHINES_URL}/TR-999", headers=AUTH).status_code == 404


# --- Critério 6: sem chave, nada muda ------------------------------------------------------------


def test_writing_without_the_api_key_returns_401_and_changes_nothing(
    client: TestClient, session: Session
) -> None:
    create(client)

    attempts = [
        client.post(MACHINES_URL, json={**TRACTOR, "code": "TR-002"}),
        client.patch(f"{MACHINES_URL}/TR-001", json={"name": "invadido"}),
        client.delete(f"{MACHINES_URL}/TR-001"),
    ]

    assert [attempt.status_code for attempt in attempts] == [401, 401, 401]
    stored = session.exec(select(Machine)).all()
    assert [(row.code, row.name) for row in stored] == [("TR-001", TRACTOR["name"])]


def test_reading_stays_open_in_dev(client: TestClient) -> None:
    """Como nas demais leituras (I5), a listagem só exige chave fora do ambiente `dev`."""
    create(client)

    assert client.get(MACHINES_URL).status_code == 200
    assert client.get(f"{MACHINES_URL}/TR-001").status_code == 200


def test_reading_requires_the_key_outside_dev(session: Session) -> None:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="production", api_keys=API_KEY
    )
    production = TestClient(app)

    assert production.get(MACHINES_URL).status_code == 401
    assert production.get(MACHINES_URL, headers=AUTH).status_code == 200


# --- Critério 7: excluir a máquina não apaga a telemetria ----------------------------------------


def test_deleting_a_linked_machine_keeps_the_device_data(
    client: TestClient, session: Session
) -> None:
    save_telemetry(session, seq=1)
    save_telemetry(session, seq=2)
    create(client, device_id=DEVICE_ID)

    before = client.get(f"/api/v1/devices/{DEVICE_ID}/telemetry/latest").json()
    assert client.delete(f"{MACHINES_URL}/TR-001", headers=AUTH).status_code == 204
    after = client.get(f"/api/v1/devices/{DEVICE_ID}/telemetry/latest")

    assert after.status_code == 200
    assert after.json() == before
    assert len(session.exec(select(Telemetry)).all()) == 2
    assert client.get(f"/api/v1/devices/{DEVICE_ID}/status").json()["state"] == "online"


# --- Critério 8 (regressão): o cadastro não mexe no limite do equipamento ------------------------


def test_a_linked_machine_does_not_change_the_device_limit(client: TestClient) -> None:
    """Regra 6: `base_tilt_limit_deg` da máquina é informativo.

    O que quebra este teste é alguém fazer o limite do W4 olhar para o cadastro — que é
    exatamente o risco declarado na feature.
    """
    before = client.get(LIMIT_URL).json()

    create(client, device_id=DEVICE_ID, base_tilt_limit_deg=5.0)
    after = client.get(LIMIT_URL).json()

    assert after == before
    assert after["reference_tilt_limit_deg"] == 15.0


def test_a_linked_machine_does_not_change_the_published_limit(
    client: TestClient, bridge: FakeBridge
) -> None:
    """O mesmo, do lado do MQTT: o payload publicado é idêntico antes e depois do cadastro."""
    assert client.post(PUBLISH_URL, headers=AUTH).status_code == 200

    create(client, device_id=DEVICE_ID, base_tilt_limit_deg=5.0)
    assert client.post(PUBLISH_URL, headers=AUTH).status_code == 200

    first, second = bridge.published[0], bridge.published[1]
    assert second["payload"] == first["payload"]
    assert second["payload"]["tilt_limit_deg"] != 5.0


# --- Critério 9 (LGPD): campo de pessoa é recusado -----------------------------------------------


def test_a_personal_field_is_refused_with_422(client: TestClient, session: Session) -> None:
    response = client.post(MACHINES_URL, headers=AUTH, json={**TRACTOR, "operador": "José"})

    assert response.status_code == 422
    assert session.exec(select(Machine)).all() == []


def test_a_personal_field_is_refused_on_a_patch(client: TestClient) -> None:
    create(client)

    response = client.patch(f"{MACHINES_URL}/TR-001", headers=AUTH, json={"operador": "José"})

    assert response.status_code == 422


# --- Critério 10: as três escritas aparecem na trilha --------------------------------------------


def test_the_three_writes_land_in_the_audit_trail(client: TestClient) -> None:
    create(client, device_id=DEVICE_ID)
    client.patch(f"{MACHINES_URL}/TR-001", headers=AUTH, json={"hour_meter_h": 3200.0})
    client.delete(f"{MACHINES_URL}/TR-001", headers=AUTH)

    entries = client.get(
        AUDIT_URL, headers=AUTH, params={"entity": "TR-001", "decision_type": "machine"}
    ).json()

    assert [entry["inputs"]["action"] for entry in entries] == ["delete", "update", "create"]
    assert {entry["entity_id"] for entry in entries} == {"TR-001"}
    assert {entry["source"] for entry in entries} == {"api"}
    assert entries[-1]["output"]["device_id"] == DEVICE_ID
    assert entries[1]["inputs"]["changed_fields"] == ["hour_meter_h"]


def test_the_audit_trail_keeps_the_key_masked_and_the_free_text_out(client: TestClient) -> None:
    """A chave nunca vai inteira para a trilha, e `notes` não é duplicado nela (LGPD)."""
    create(client)

    entry = client.get(AUDIT_URL, headers=AUTH, params={"entity": "TR-001"}).json()[0]

    assert entry["inputs"]["api_key"] == "****1234"
    assert API_KEY not in json.dumps(entry)
    assert TRACTOR["notes"] not in json.dumps(entry)


def test_a_refused_write_leaves_no_trace_in_the_trail(client: TestClient) -> None:
    """A trilha registra o que aconteceu, não o que foi tentado e recusado pela regra."""
    create(client, device_id="trator-fantasma")

    assert client.get(AUDIT_URL, headers=AUTH, params={"decision_type": "machine"}).json() == []


def test_the_audit_entry_carries_the_request_id(client: TestClient) -> None:
    request_id = "requisicao-de-teste"

    client.post(MACHINES_URL, headers={**AUTH, "X-Request-ID": request_id}, json=TRACTOR)

    entry = client.get(AUDIT_URL, headers=AUTH, params={"entity": "TR-001"}).json()[0]
    assert entry["request_id"] == request_id


# --- Datas -------------------------------------------------------------------------------------


def test_the_timestamps_are_filled_on_creation(client: TestClient) -> None:
    body = create(client).json()

    created_at = datetime.fromisoformat(body["created_at"])
    assert abs(datetime.now(UTC).replace(tzinfo=None) - created_at) < timedelta(minutes=5)
    assert body["updated_at"] == body["created_at"]
