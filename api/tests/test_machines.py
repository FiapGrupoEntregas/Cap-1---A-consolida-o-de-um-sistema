"""Testes das regras do cadastro de maquinário (W14).

Aqui moram as regras 1 a 8 uma a uma, sobre funções **puras** (`validate_machine` recebe o que o
banco e o catálogo já responderam) e sobre as bordas de cada limite declarado nos schemas. As
regras vistas pelo HTTP estão em `tests/test_machines_route.py`.
"""

from collections.abc import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import Machine
from app.repositories import machines as machines_repository
from app.schemas.machine import (
    CODE_MAX_LENGTH,
    MAX_HOUR_METER_H,
    MAX_MANUFACTURING_YEAR,
    MAX_TILT_LIMIT_DEG,
    MIN_MANUFACTURING_YEAR,
    NOTES_MAX_LENGTH,
    MachineCreate,
    MachineUpdate,
)
from app.services.machines import (
    LinkContext,
    MachineErrorKind,
    MachineRuleError,
    build_context,
    create_machine,
    normalize_code,
    update_machine,
    validate_machine,
)

FARM_ID = "cafe-carmo-de-minas"
OTHER_FARM_ID = "graos-sorriso"
DEVICE_ID = "tractor-01"


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def payload(**overrides: object) -> MachineCreate:
    """Um cadastro mínimo válido, com o que o teste quiser trocar."""
    return MachineCreate.model_validate(
        {"code": "TR-001", "name": "Trator 1", "type": "tractor", **overrides}
    )


# --- Regra 1: `code` é a identidade da máquina ---------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("tr-001", "TR-001"),
        ("  TR-001  ", "TR-001"),
        ("\ttr-001\n", "TR-001"),
        ("TR-001", "TR-001"),
    ],
)
def test_the_code_is_normalized_to_upper_case_without_padding(raw: str, expected: str) -> None:
    assert normalize_code(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\n\t"])
def test_a_blank_code_is_refused(raw: str) -> None:
    with pytest.raises(MachineRuleError) as error:
        normalize_code(raw)
    assert error.value.kind is MachineErrorKind.INVALID_CODE


@pytest.mark.parametrize("length", [1, CODE_MAX_LENGTH - 1, CODE_MAX_LENGTH])
def test_the_code_accepts_up_to_thirty_two_characters(length: int) -> None:
    """Borda do limite: 32 entra, 33 não (o teste seguinte)."""
    assert len(normalize_code("A" * length)) == length


def test_a_code_above_the_limit_is_refused() -> None:
    with pytest.raises(MachineRuleError) as error:
        normalize_code("A" * (CODE_MAX_LENGTH + 1))
    assert error.value.kind is MachineErrorKind.INVALID_CODE


def test_the_code_limit_is_thirty_two() -> None:
    """Âncora do valor: o limite da W14 regra 1 é 32, e não o que a constante disser hoje."""
    assert CODE_MAX_LENGTH == 32


def test_a_repeated_code_is_a_conflict() -> None:
    with pytest.raises(MachineRuleError) as error:
        _validate(code_taken=True)
    assert error.value.kind is MachineErrorKind.DUPLICATE_CODE
    assert "TR-001" in error.value.message


# --- Regras 2 a 5: fazenda, dispositivo e coerência do vínculo -----------------------------------


def _validate(
    code: str = "TR-001",
    farm_id: str | None = None,
    device_id: str | None = None,
    **context: object,
) -> None:
    """Roda `validate_machine` com um contexto válido por padrão."""
    validate_machine(code, farm_id, device_id, LinkContext(**context))  # type: ignore[arg-type]


def test_a_machine_without_farm_or_device_is_valid() -> None:
    _validate()


def test_an_unknown_farm_is_refused() -> None:
    with pytest.raises(MachineRuleError) as error:
        _validate(farm_id="fazenda-fantasma", farm_known=False)
    assert error.value.kind is MachineErrorKind.UNKNOWN_FARM


def test_an_unknown_farm_is_ignored_when_no_farm_was_declared() -> None:
    """Sem `farm_id`, a existência da fazenda não é assunto: a máquina é válida."""
    _validate(farm_id=None, farm_known=False)


def test_an_unknown_device_is_refused() -> None:
    with pytest.raises(MachineRuleError) as error:
        _validate(device_id="trator-fantasma", device_known=False)
    assert error.value.kind is MachineErrorKind.UNKNOWN_DEVICE


def test_a_device_from_another_farm_is_refused() -> None:
    """Regra 5: um ESP32 da fazenda A não está instalado numa máquina da fazenda B."""
    with pytest.raises(MachineRuleError) as error:
        _validate(farm_id=OTHER_FARM_ID, device_id=DEVICE_ID, device_farm_id=FARM_ID)
    assert error.value.kind is MachineErrorKind.FARM_MISMATCH
    assert FARM_ID in error.value.message
    assert OTHER_FARM_ID in error.value.message


def test_a_device_from_the_same_farm_is_accepted() -> None:
    _validate(farm_id=FARM_ID, device_id=DEVICE_ID, device_farm_id=FARM_ID)


def test_a_device_without_declared_farm_is_accepted() -> None:
    """A coerência só é cobrada quando a máquina **declara** a fazenda (regra 5)."""
    _validate(farm_id=None, device_id=DEVICE_ID, device_farm_id=FARM_ID)


def test_a_device_already_linked_is_a_conflict() -> None:
    with pytest.raises(MachineRuleError) as error:
        _validate(device_id=DEVICE_ID, device_owner_code="TR-009")
    assert error.value.kind is MachineErrorKind.DEVICE_TAKEN
    assert "TR-009" in error.value.message


def test_an_unknown_device_loses_to_a_taken_one() -> None:
    """Ordem proposital: o que **não existe** é dito antes do que está ocupado."""
    with pytest.raises(MachineRuleError) as error:
        _validate(device_id=DEVICE_ID, device_known=False, device_owner_code="TR-009")
    assert error.value.kind is MachineErrorKind.UNKNOWN_DEVICE


# --- Contexto montado a partir do banco e do catálogo --------------------------------------------


def test_the_context_reads_the_real_catalog(session: Session) -> None:
    context = build_context(session, "TR-001", FARM_ID, DEVICE_ID, machine_id=None)

    assert context == LinkContext(
        code_taken=False,
        farm_known=True,
        device_known=True,
        device_farm_id=FARM_ID,
        device_owner_code=None,
    )


def test_the_context_sees_an_unknown_farm_and_device(session: Session) -> None:
    context = build_context(session, "TR-001", "fazenda-fantasma", "trator-fantasma", None)

    assert (context.farm_known, context.device_known, context.device_farm_id) == (
        False,
        False,
        None,
    )


def test_a_machine_is_not_its_own_competitor(session: Session) -> None:
    """Sem excluir a própria linha, um `PATCH` que não mexe no vínculo se acusaria."""
    machine = create_machine(session, payload(farm_id=FARM_ID, device_id=DEVICE_ID))

    own = build_context(session, machine.code, FARM_ID, DEVICE_ID, machine_id=machine.id)
    other = build_context(session, machine.code, FARM_ID, DEVICE_ID, machine_id=None)

    assert (own.code_taken, own.device_owner_code) == (False, None)
    assert (other.code_taken, other.device_owner_code) == (True, "TR-001")


# --- Gravação: criação e edição ------------------------------------------------------------------


def test_creating_stores_the_normalized_code(session: Session) -> None:
    machine = create_machine(session, payload(code=" tr-007 "))

    assert machine.code == "TR-007"
    assert machines_repository.get_by_code(session, "TR-007") is not None


def test_a_second_machine_cannot_take_the_same_device(session: Session) -> None:
    create_machine(session, payload(code="TR-001", device_id=DEVICE_ID))

    with pytest.raises(MachineRuleError) as error:
        create_machine(session, payload(code="TR-002", device_id=DEVICE_ID))

    assert error.value.kind is MachineErrorKind.DEVICE_TAKEN
    assert "TR-001" in error.value.message


def test_unlinking_frees_the_device_for_another_machine(session: Session) -> None:
    first = create_machine(session, payload(code="TR-001", device_id=DEVICE_ID))

    update_machine(session, first, MachineUpdate.model_validate({"device_id": None}))
    second = create_machine(session, payload(code="TR-002", device_id=DEVICE_ID))

    assert first.device_id is None
    assert second.device_id == DEVICE_ID


def test_editing_only_touches_the_fields_that_came(session: Session) -> None:
    machine = create_machine(session, payload(manufacturer="John Deere", year=2019))

    update_machine(session, machine, MachineUpdate.model_validate({"name": "Trator 1 (revisado)"}))

    assert (machine.name, machine.manufacturer, machine.year) == (
        "Trator 1 (revisado)",
        "John Deere",
        2019,
    )


def test_an_explicit_null_clears_the_field(session: Session) -> None:
    machine = create_machine(session, payload(manufacturer="John Deere"))

    update_machine(session, machine, MachineUpdate.model_validate({"manufacturer": None}))

    assert machine.manufacturer is None


def test_editing_carries_the_stored_link_into_the_rules(session: Session) -> None:
    """A regra roda sobre o **estado resultante**, não sobre o corpo da requisição.

    A máquina já é da fazenda do café; declarar só a outra fazenda tem de esbarrar no vínculo que
    continua gravado.
    """
    machine = create_machine(session, payload(farm_id=FARM_ID, device_id=DEVICE_ID))

    with pytest.raises(MachineRuleError) as error:
        update_machine(session, machine, MachineUpdate.model_validate({"farm_id": OTHER_FARM_ID}))

    assert error.value.kind is MachineErrorKind.FARM_MISMATCH


def test_editing_the_code_to_one_that_exists_is_a_conflict(session: Session) -> None:
    create_machine(session, payload(code="TR-001"))
    second = create_machine(session, payload(code="TR-002"))

    with pytest.raises(MachineRuleError) as error:
        update_machine(session, second, MachineUpdate.model_validate({"code": "tr-001"}))

    assert error.value.kind is MachineErrorKind.DUPLICATE_CODE


def test_deleting_removes_only_the_machine_row(session: Session) -> None:
    """Regra 7: telemetria e evento são do dispositivo e não saem junto."""
    machine = create_machine(session, payload(device_id=DEVICE_ID))

    machines_repository.delete(session, machine)

    assert machines_repository.get_by_code(session, "TR-001") is None
    assert machines_repository.get_by_device_id(session, DEVICE_ID) is None


# --- Filtros da listagem -------------------------------------------------------------------------


def test_the_listing_filters_by_farm_type_and_link(session: Session) -> None:
    create_machine(session, payload(code="TR-001", farm_id=FARM_ID, device_id=DEVICE_ID))
    create_machine(session, payload(code="CO-001", type="Harvester", farm_id=OTHER_FARM_ID))
    create_machine(session, payload(code="TR-002", type="tractor"))

    def codes(**filters: object) -> list[str]:
        rows = machines_repository.list_machines(session, **filters)  # type: ignore[arg-type]
        return [row.code for row in rows]

    assert codes() == ["CO-001", "TR-001", "TR-002"]
    assert codes(farm_id=FARM_ID) == ["TR-001"]
    assert codes(machine_type="harvester") == ["CO-001"]
    assert codes(linked=True) == ["TR-001"]
    assert codes(linked=False) == ["CO-001", "TR-002"]


# --- Regra 6 e os limites dos campos (bordas) ----------------------------------------------------


@pytest.mark.parametrize("value", [0.1, 1.0, MAX_TILT_LIMIT_DEG])
def test_the_informative_tilt_limit_accepts_the_open_interval(value: float) -> None:
    """Regra 6: `(0, 90]` — 90 entra."""
    assert payload(base_tilt_limit_deg=value).base_tilt_limit_deg == value


@pytest.mark.parametrize("value", [0.0, -0.1, MAX_TILT_LIMIT_DEG + 0.1])
def test_the_informative_tilt_limit_refuses_outside_the_interval(value: float) -> None:
    """Regra 6: `0` (fechado à esquerda) e qualquer coisa acima de 90 são recusados."""
    with pytest.raises(ValidationError):
        payload(base_tilt_limit_deg=value)


def test_the_tilt_limit_interval_is_zero_to_ninety() -> None:
    """Âncora do valor: a faixa da W14 regra 6 é (0, 90]."""
    assert MAX_TILT_LIMIT_DEG == 90.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("year", MIN_MANUFACTURING_YEAR),
        ("year", MAX_MANUFACTURING_YEAR),
        ("hour_meter_h", 0.0),
        ("hour_meter_h", MAX_HOUR_METER_H),
        ("notes", "n" * NOTES_MAX_LENGTH),
        ("code", "A" * CODE_MAX_LENGTH),
    ],
)
def test_the_borders_of_each_field_are_accepted(field: str, value: object) -> None:
    assert getattr(payload(**{field: value}), field) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("year", MIN_MANUFACTURING_YEAR - 1),
        ("year", MAX_MANUFACTURING_YEAR + 1),
        ("hour_meter_h", -0.1),
        ("hour_meter_h", MAX_HOUR_METER_H + 1),
        ("notes", "n" * (NOTES_MAX_LENGTH + 1)),
        ("code", "A" * (CODE_MAX_LENGTH + 1)),
        ("name", "   "),
        ("type", ""),
    ],
)
def test_just_outside_each_border_is_refused(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        payload(**{field: value})


def test_blank_optional_text_becomes_null(session: Session) -> None:
    """O formulário devolve `""` no campo não preenchido, e isso é ausência de valor."""
    machine = create_machine(session, payload(manufacturer="  ", device_id="", notes=""))

    assert (machine.manufacturer, machine.device_id, machine.notes) == (None, None, None)


# --- Regra 8 (LGPD) e "não informado" × "limpar" -------------------------------------------------


@pytest.mark.parametrize("model", [MachineCreate, MachineUpdate])
def test_a_personal_field_is_refused_on_the_way_in(model: type) -> None:
    """Regra 8: `extra="forbid"` recusa `operador` em vez de gravá-lo."""
    with pytest.raises(ValidationError):
        model.model_validate(
            {"code": "TR-001", "name": "Trator 1", "type": "tractor", "operador": "José"}
        )


def test_an_absent_field_is_not_a_change() -> None:
    assert MachineUpdate.model_validate({"name": "Trator 1"}).changes() == {"name": "Trator 1"}


def test_an_explicit_null_is_a_change() -> None:
    """É por aqui que a tela desvincula um ESP32."""
    assert MachineUpdate.model_validate({"device_id": None}).changes() == {"device_id": None}


def test_an_empty_patch_changes_nothing() -> None:
    assert MachineUpdate.model_validate({}).changes() == {}


@pytest.mark.parametrize("field", ["code", "name", "type", "active"])
def test_the_identity_fields_cannot_be_cleared(field: str) -> None:
    with pytest.raises(ValidationError):
        MachineUpdate.model_validate({field: None})


# --- Modelo --------------------------------------------------------------------------------------


def test_two_machines_can_live_without_a_device(session: Session) -> None:
    """`device_id` é único, mas no SQLite vários `NULL` convivem: máquina sem ESP32 é válida."""
    create_machine(session, payload(code="TR-001"))
    create_machine(session, payload(code="TR-002"))

    rows = machines_repository.list_machines(session, linked=False)

    assert [row.code for row in rows] == ["TR-001", "TR-002"]
    assert all(isinstance(row, Machine) for row in rows)
