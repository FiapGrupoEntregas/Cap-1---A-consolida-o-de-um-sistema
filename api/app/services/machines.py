"""Regras do cadastro de maquinário (W14).

O que esta camada garante, uma regra por função pura:

1. `code` é a identidade humana da máquina: normalizado para maiúsculas sem espaços nas pontas,
   de 1 a 32 caracteres, e **único**.
2. `device_id` precisa existir no catálogo do W1 (`app/data/farms.json`), que segue somente leitura.
3. Um dispositivo pertence a **no máximo uma** máquina.
4. `farm_id` precisa existir no catálogo.
5. Se a máquina declara `farm_id` e o dispositivo é de **outra** fazenda, o vínculo é recusado: um
   ESP32 da fazenda A não está instalado numa máquina da fazenda B.
6. `base_tilt_limit_deg` da máquina é **informativo** — a faixa `(0, 90]` está no schema e o valor
   **não** entra em conta nenhuma. O limite que vai para o equipamento continua vindo do catálogo
   e de `document/regras-de-risco.md` §4 (`app/services/limits.py`), e o teste de regressão
   `test_machines_route.py::test_linked_machine_does_not_change_the_published_limit` prova isso.
7. Excluir a máquina não apaga telemetria nem evento: eles são do dispositivo
   (`app/repositories/machines.py::delete`).
8. Nenhum dado pessoal entra aqui — os schemas usam `extra="forbid"` (LGPD, ADR-011).

As checagens ficam em `validate_machine`, que recebe o que o banco e o catálogo já responderam
(`LinkContext`) e **não** faz I/O. As funções com `session` só montam esse contexto e gravam.
"""

from dataclasses import dataclass
from enum import StrEnum

from sqlmodel import Session

from app.core.clock import now_local
from app.models import Machine
from app.repositories import devices as devices_repository
from app.repositories import machines as machines_repository
from app.schemas.device import DeviceStatusResponse
from app.schemas.machine import (
    CODE_MAX_LENGTH,
    LinkedDevice,
    MachineCreate,
    MachineUpdate,
    MachineWithDevice,
)
from app.services import devices as devices_service
from app.services import farms as farms_service


class MachineErrorKind(StrEnum):
    """Por que a regra recusou. A rota traduz cada um em 409 ou 422 — aqui não se fala HTTP."""

    INVALID_CODE = "invalid_code"
    DUPLICATE_CODE = "duplicate_code"
    UNKNOWN_FARM = "unknown_farm"
    UNKNOWN_DEVICE = "unknown_device"
    DEVICE_TAKEN = "device_taken"
    FARM_MISMATCH = "farm_mismatch"


class MachineRuleError(ValueError):
    """Uma regra do cadastro foi violada. `kind` diz qual, `message` é o texto para o usuário."""

    def __init__(self, kind: MachineErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


@dataclass(frozen=True)
class LinkContext:
    """O que o banco e o catálogo já responderam sobre a máquina que vai ser gravada.

    Separar a consulta da decisão é o que deixa `validate_machine` pura e testável sem banco.
    """

    # Já existe **outra** máquina com o mesmo `code`?
    code_taken: bool = False
    # A fazenda informada existe no catálogo? (irrelevante quando `farm_id` é nulo)
    farm_known: bool = True
    # O dispositivo informado existe no catálogo? (irrelevante quando `device_id` é nulo)
    device_known: bool = True
    # De qual fazenda o dispositivo é, segundo o catálogo.
    device_farm_id: str | None = None
    # `code` da **outra** máquina que já usa esse dispositivo, se houver.
    device_owner_code: str | None = None


def normalize_code(raw: str) -> str:
    """Regra 1: maiúsculas, sem espaços nas pontas, de 1 a 32 caracteres."""
    code = raw.strip().upper()
    if not code:
        raise MachineRuleError(
            MachineErrorKind.INVALID_CODE, "O código da máquina não pode ficar em branco."
        )
    if len(code) > CODE_MAX_LENGTH:
        raise MachineRuleError(
            MachineErrorKind.INVALID_CODE,
            f"O código da máquina pode ter no máximo {CODE_MAX_LENGTH} caracteres.",
        )
    return code


def validate_machine(
    code: str, farm_id: str | None, device_id: str | None, context: LinkContext
) -> None:
    """Aplica as regras 1 a 5 sobre um cadastro já normalizado. Função pura.

    A ordem é proposital: primeiro o que **não existe** (o usuário digitou errado), depois o que
    já está ocupado — assim o erro devolvido é o mais acionável dos dois.
    """
    if context.code_taken:
        raise MachineRuleError(
            MachineErrorKind.DUPLICATE_CODE, f"Já existe uma máquina com o código '{code}'."
        )

    if farm_id is not None and not context.farm_known:
        raise MachineRuleError(
            MachineErrorKind.UNKNOWN_FARM, f"Fazenda '{farm_id}' não existe no catálogo."
        )

    if device_id is None:
        return

    if not context.device_known:
        raise MachineRuleError(
            MachineErrorKind.UNKNOWN_DEVICE, f"Equipamento '{device_id}' não existe no catálogo."
        )

    if farm_id is not None and context.device_farm_id != farm_id:
        raise MachineRuleError(
            MachineErrorKind.FARM_MISMATCH,
            f"O equipamento '{device_id}' é da fazenda '{context.device_farm_id}', "
            f"e a máquina está na fazenda '{farm_id}'.",
        )

    if context.device_owner_code is not None:
        raise MachineRuleError(
            MachineErrorKind.DEVICE_TAKEN,
            f"O equipamento '{device_id}' já está vinculado à máquina "
            f"'{context.device_owner_code}'.",
        )


def build_context(
    session: Session, code: str, farm_id: str | None, device_id: str | None, machine_id: int | None
) -> LinkContext:
    """Consulta banco e catálogo e monta o contexto de `validate_machine`.

    `machine_id` é a máquina que está sendo editada: ela não conta como concorrente do próprio
    `code` nem do próprio `device_id` — sem isso, um `PATCH` que não mexe no vínculo se acusaria.
    """
    by_code = machines_repository.get_by_code(session, code)
    code_taken = by_code is not None and by_code.id != machine_id

    farm_known = farm_id is None or farms_service.get_farm(farm_id) is not None

    device_known = True
    device_farm_id: str | None = None
    device_owner_code: str | None = None
    if device_id is not None:
        found = farms_service.find_device(device_id)
        device_known = found is not None
        if found is not None:
            device_farm_id = found[0].id
        owner = machines_repository.get_by_device_id(session, device_id)
        if owner is not None and owner.id != machine_id:
            device_owner_code = owner.code

    return LinkContext(
        code_taken=code_taken,
        farm_known=farm_known,
        device_known=device_known,
        device_farm_id=device_farm_id,
        device_owner_code=device_owner_code,
    )


def create_machine(session: Session, payload: MachineCreate) -> Machine:
    """Valida e grava uma máquina nova. Levanta `MachineRuleError` se alguma regra barrar."""
    code = normalize_code(payload.code)
    context = build_context(session, code, payload.farm_id, payload.device_id, machine_id=None)
    validate_machine(code, payload.farm_id, payload.device_id, context)

    machine = Machine(**{**payload.model_dump(), "code": code})
    return machines_repository.insert(session, machine)


def update_machine(session: Session, machine: Machine, payload: MachineUpdate) -> Machine:
    """Aplica uma edição parcial já validada.

    As chaves ausentes do JSON não chegam aqui (`MachineUpdate.changes()`), então o estado
    resultante é "o que veio, senão o que já estava" — e é sobre **esse** estado que as regras
    rodam, não sobre o corpo da requisição.
    """
    changes = payload.changes()
    if "code" in changes:
        changes["code"] = normalize_code(changes["code"])

    code = changes.get("code", machine.code)
    farm_id = changes.get("farm_id", machine.farm_id)
    device_id = changes.get("device_id", machine.device_id)

    context = build_context(session, code, farm_id, device_id, machine_id=machine.id)
    validate_machine(code, farm_id, device_id, context)

    return machines_repository.update(session, machine, changes)


def linked_device(session: Session, device_id: str | None) -> LinkedDevice | None:
    """O dispositivo vinculado, com o estado ao vivo do W5.

    Devolve `None` quando a máquina não tem ESP32 **ou** quando o `device_id` gravado saiu do
    catálogo depois do cadastro — o catálogo é a fonte da verdade, e uma máquina órfã não deve
    derrubar a tela.
    """
    if device_id is None:
        return None

    found = farms_service.find_device(device_id)
    if found is None:
        return None
    farm, device = found

    status_row = devices_repository.latest_status(session, device_id)
    latest = devices_repository.latest_telemetry(session, device_id)
    state, last_seen_at, silence_s = devices_service.resolve_state(
        status_row, latest, devices_repository.utc_naive(now_local())
    )

    return LinkedDevice(
        device=device,
        farm_id=farm.id,
        farm_name=farm.name,
        status=DeviceStatusResponse(
            device_id=device_id,
            state=state,
            reported_state=devices_service.reported_state(status_row),
            last_seen_at=last_seen_at,
            seconds_since_last_telemetry=round(silence_s, 1) if silence_s is not None else None,
        ),
    )


def to_detail(session: Session, machine: Machine) -> MachineWithDevice:
    """Monta a resposta completa da máquina, com o dispositivo vinculado quando houver."""
    detail = MachineWithDevice.model_validate(machine, from_attributes=True)
    detail.device = linked_device(session, machine.device_id)
    return detail
