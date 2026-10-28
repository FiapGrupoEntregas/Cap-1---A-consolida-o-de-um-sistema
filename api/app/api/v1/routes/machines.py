"""Cadastro de maquinário e vínculo com o ESP32 (W14).

A rota só traduz HTTP: as regras estão em `app/services/machines.py` e o SQL em
`app/repositories/machines.py`. O catálogo do W1 (`app/data/farms.json`) continua **somente
leitura** — aqui ninguém cria fazenda nem dispositivo, só aponta para os que já existem.

Escrita exige `X-API-Key` (I5, ADR-013) e deixa rastro em `decision_log`.
"""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlmodel import Session

from app.core.logging import request_id_var
from app.core.security import ApiKeyDep, require_api_key, require_read_access
from app.db import get_session
from app.models import Machine
from app.repositories import audit as audit_repository
from app.repositories import machines as machines_repository
from app.schemas.audit import DecisionSource, DecisionType
from app.schemas.machine import (
    MachineCreate,
    MachineResponse,
    MachineUpdate,
    MachineWithDevice,
)
from app.services import machines as machines_service
from app.services.machines import MachineErrorKind, MachineRuleError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/machines", tags=["machines"])

MACHINE_NOT_FOUND_MESSAGE = "Máquina não encontrada"

# Como cada regra recusada (W14) vira resposta HTTP. **Esta é a única tradução de regra para
# status no projeto**: o serviço fala em `MachineErrorKind`, não em números.
#
# - 409 (conflito): o dado existe e já está ocupado — só muda quem desocupa.
# - 422 (não processável): o dado aponta para algo que não existe ou é incoerente.
STATUS_BY_ERROR_KIND = {
    MachineErrorKind.INVALID_CODE: status.HTTP_422_UNPROCESSABLE_ENTITY,
    MachineErrorKind.DUPLICATE_CODE: status.HTTP_409_CONFLICT,
    MachineErrorKind.UNKNOWN_FARM: status.HTTP_422_UNPROCESSABLE_ENTITY,
    MachineErrorKind.UNKNOWN_DEVICE: status.HTTP_422_UNPROCESSABLE_ENTITY,
    MachineErrorKind.DEVICE_TAKEN: status.HTTP_409_CONFLICT,
    MachineErrorKind.FARM_MISMATCH: status.HTTP_422_UNPROCESSABLE_ENTITY,
}

SessionDep = Annotated[Session, Depends(get_session)]

CodePath = Annotated[str, Path(description="Código da máquina (ex.: TR-001).")]

FarmIdQuery = Annotated[str | None, Query(description="Filtra pelas máquinas de uma fazenda.")]
TypeQuery = Annotated[
    str | None, Query(alias="type", description="Filtra pelo tipo (ex.: tractor).")
]
LinkedQuery = Annotated[
    bool | None,
    Query(description="`true` só as que têm ESP32 vinculado, `false` só as que não têm."),
]


@router.get(
    "",
    response_model=list[MachineResponse],
    dependencies=[Depends(require_read_access)],
)
def list_machines(
    session: SessionDep,
    farm_id: FarmIdQuery = None,
    machine_type: TypeQuery = None,
    linked: LinkedQuery = None,
) -> list[MachineResponse]:
    """Máquinas cadastradas, em ordem de código, com os filtros da tela (W14).

    Filtro em branco é **ausência de filtro**, não filtro por vazio: o `selectbox` do Streamlit
    devolve `""` para "todas", e tratar isso como valor faria a tela mostrar "nenhuma máquina" com
    o banco cheio. Mesma convenção do texto opcional nos schemas (`_optional_text`).
    """
    rows = machines_repository.list_machines(
        session,
        farm_id=(farm_id or "").strip() or None,
        machine_type=(machine_type or "").strip() or None,
        linked=linked,
    )
    return [MachineResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post(
    "",
    response_model=MachineWithDevice,
    status_code=status.HTTP_201_CREATED,
    # A chave é dependência **do decorador**, então o FastAPI a resolve antes de qualquer
    # parâmetro: sem chave, a requisição para aqui e nada é gravado. O parâmetro `api_key` logo
    # abaixo reaproveita a mesma chamada (o FastAPI cacheia a dependência por requisição) só para
    # ter a chave **mascarada** que vai para a trilha de auditoria.
    dependencies=[Depends(require_api_key)],
)
def create_machine(
    payload: MachineCreate,
    session: SessionDep,
    request: Request,
    response: Response,
    api_key: ApiKeyDep,
) -> MachineWithDevice:
    """Cadastra uma máquina. **201** com `Location` apontando para ela (W14)."""
    machine = _apply(lambda: machines_service.create_machine(session, payload))
    _record(session, machine, action="create", api_key=api_key)

    response.headers["Location"] = str(request.url_for("get_machine", code=machine.code))
    return machines_service.to_detail(session, machine)


@router.get(
    "/{code}",
    response_model=MachineWithDevice,
    dependencies=[Depends(require_read_access)],
)
def get_machine(code: CodePath, session: SessionDep) -> MachineWithDevice:
    """Uma máquina, com o dispositivo vinculado e o estado ao vivo dele (W14 + W5)."""
    return machines_service.to_detail(session, _require_machine(session, code))


@router.patch(
    "/{code}",
    response_model=MachineWithDevice,
    dependencies=[Depends(require_api_key)],
)
def update_machine(
    code: CodePath, payload: MachineUpdate, session: SessionDep, api_key: ApiKeyDep
) -> MachineWithDevice:
    """Edição parcial. O campo ausente do JSON não muda; o campo com `null` é limpo (W14)."""
    machine = _require_machine(session, code)
    changed = sorted(payload.changes())
    machine = _apply(lambda: machines_service.update_machine(session, machine, payload))
    _record(session, machine, action="update", api_key=api_key, changed_fields=changed)

    return machines_service.to_detail(session, machine)


@router.delete(
    "/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_api_key)],
)
def delete_machine(code: CodePath, session: SessionDep, api_key: ApiKeyDep) -> Response:
    """Exclui a máquina. **204**.

    A telemetria e os eventos do dispositivo **continuam no banco** (W14 regra 7): eles são do
    ESP32, não da máquina. A exclusão só desfaz o vínculo.
    """
    machine = _require_machine(session, code)
    _record(session, machine, action="delete", api_key=api_key)
    machines_repository.delete(session, machine)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- internos ------------------------------------------------------------------------------------


def _require_machine(session: Session, code: str) -> Machine:
    """Busca pelo código normalizado (`tr-001` acha `TR-001`) ou devolve 404."""
    try:
        normalized = machines_service.normalize_code(code)
    except MachineRuleError as error:
        raise _http_error(error) from error

    machine = machines_repository.get_by_code(session, normalized)
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MACHINE_NOT_FOUND_MESSAGE)
    return machine


def _apply(action: Callable[[], Machine]) -> Machine:
    """Roda a operação do serviço e converte a regra violada no status certo."""
    try:
        return action()
    except MachineRuleError as error:
        raise _http_error(error) from error


def _http_error(error: MachineRuleError) -> HTTPException:
    """Traduz `MachineErrorKind` em 409 ou 422, com a mensagem do serviço."""
    return HTTPException(
        status_code=STATUS_BY_ERROR_KIND[error.kind],
        detail=error.message,
    )


def _record(
    session: Session,
    machine: Machine,
    action: str,
    api_key: str,
    changed_fields: list[str] | None = None,
) -> None:
    """Registra a escrita na trilha de auditoria (I5).

    ⚠️ Só vão para a trilha os campos **estruturais** — quem é a máquina e a que ela está
    vinculada. O texto livre de `notes` fica de fora de propósito: a trilha não é lugar para
    duplicar conteúdo que o usuário digitou (LGPD, ADR-011). Da edição guarda-se a **lista de
    nomes** dos campos alterados, não os valores.
    """
    audit_repository.record_decision(
        session,
        decision_type=DecisionType.MACHINE,
        entity_id=machine.code,
        inputs={
            "action": action,
            "code": machine.code,
            "api_key": api_key,
            "changed_fields": changed_fields,
        },
        output={
            "code": machine.code,
            "type": machine.type,
            "farm_id": machine.farm_id,
            "device_id": machine.device_id,
            "active": machine.active,
        },
        source=DecisionSource.API,
        request_id=request_id_var.get(),
        # Nenhum modelo preditivo participa de um cadastro: gravar uma versão aqui seria ruído.
        model_version=None,
    )
