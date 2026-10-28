"""Leitura e escrita do cadastro de maquinário (W14).

Só SQL: nenhuma regra de negócio mora aqui. Quem decide se um `code` pode repetir, se o
`device_id` existe no catálogo ou se a fazenda bate é `app/services/machines.py`.

Como nos outros repositórios (I3), toda função recebe a `Session` de quem chama.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Machine
from app.repositories.devices import utc_naive


def _now() -> datetime:
    """Agora em UTC sem fuso, que é como o SQLite guarda data e hora."""
    return utc_naive(datetime.now(UTC))


def get_by_code(session: Session, code: str) -> Machine | None:
    """Máquina pelo `code` já normalizado, ou `None`."""
    return session.exec(select(Machine).where(Machine.code == code)).first()


def get_by_device_id(session: Session, device_id: str) -> Machine | None:
    """Máquina que já usa aquele `device_id`, ou `None`. É o que torna o vínculo exclusivo."""
    return session.exec(select(Machine).where(Machine.device_id == device_id)).first()


def list_machines(
    session: Session,
    farm_id: str | None = None,
    machine_type: str | None = None,
    linked: bool | None = None,
) -> list[Machine]:
    """Máquinas em ordem de `code`, com os filtros da tela.

    `machine_type` compara **sem diferenciar maiúsculas**: quem digitou "Tractor" no cadastro
    continua aparecendo no filtro `type=tractor`. `linked` separa as que têm ESP32 das que não têm.
    """
    statement = select(Machine)
    if farm_id is not None:
        statement = statement.where(Machine.farm_id == farm_id)
    if machine_type is not None:
        statement = statement.where(func.lower(col(Machine.type)) == machine_type.strip().lower())
    if linked is True:
        statement = statement.where(col(Machine.device_id).is_not(None))
    elif linked is False:
        statement = statement.where(col(Machine.device_id).is_(None))

    return list(session.exec(statement.order_by(col(Machine.code))))


def insert(session: Session, machine: Machine) -> Machine:
    """Grava a máquina nova e devolve a linha com `id` e datas preenchidos."""
    moment = _now()
    machine.created_at = moment
    machine.updated_at = moment
    session.add(machine)
    session.commit()
    session.refresh(machine)
    return machine


def update(session: Session, machine: Machine, changes: dict[str, Any]) -> Machine:
    """Aplica os campos informados e carimba `updated_at`.

    `changes` vem de `MachineUpdate.changes()`: as chaves ausentes já ficaram de fora, e uma chave
    com `None` significa **limpar** aquele campo.
    """
    for field, value in changes.items():
        setattr(machine, field, value)
    machine.updated_at = _now()
    session.add(machine)
    session.commit()
    session.refresh(machine)
    return machine


def delete(session: Session, machine: Machine) -> None:
    """Apaga só a linha da máquina.

    Telemetria e eventos são do **dispositivo**, não da máquina (W14 regra 7): nada em
    `telemetry`, `device_event` ou `device_status` é tocado aqui.
    """
    session.delete(machine)
    session.commit()
