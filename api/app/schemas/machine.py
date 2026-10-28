"""Schemas do cadastro de maquinário (W14).

O cadastro descreve o **bem patrimonial** — modelo, fabricante, ano, horímetro — e o vínculo
opcional com um `device_id` do catálogo do W1. As regras de negócio (código único, vínculo
exclusivo, coerência com a fazenda) ficam em `app/services/machines.py`; aqui só moram o formato
e os limites de cada campo.

⚠️ **LGPD (ADR-011):** todos os schemas de entrada usam `extra="forbid"`, então um campo como
`operador` é recusado com **422** em vez de virar coluna. `notes` é texto livre **sobre o
equipamento** e tem tamanho limitado.
"""

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.device import DeviceStatusResponse
from app.schemas.farm import Device

# W14 regra 1 — `code` é a identidade humana da máquina (ex.: `TR-001`)
CODE_MAX_LENGTH = 32

# Tamanhos de texto: suficientes para o que a tela mostra, curtos o bastante para não virar dossiê
NAME_MAX_LENGTH = 120
TYPE_MAX_LENGTH = 40
BRAND_MAX_LENGTH = 80
NOTES_MAX_LENGTH = 500

# Faixa aceita para o ano de fabricação. Fixa de propósito (em vez de "ano atual + 1"): validação
# que depende do relógio dá teste que muda de resultado na virada do ano.
MIN_MANUFACTURING_YEAR = 1900
MAX_MANUFACTURING_YEAR = 2100

# W14 regra 6 — `base_tilt_limit_deg` é **informativo** e precisa estar em (0, 90]. Ele **não**
# altera o limite calculado pelo W4: quem manda é o catálogo + regras-de-risco §4.
MIN_TILT_LIMIT_DEG = 0.0
MAX_TILT_LIMIT_DEG = 90.0

# Horímetro: um trator com 200 000 h já passou de qualquer vida útil real; o teto só barra digitação
MAX_HOUR_METER_H = 200_000.0

# Campos de `MachineUpdate` que **não** podem ser limpos: a máquina deixaria de ser identificável.
NON_CLEARABLE_FIELDS = ("code", "name", "type", "active")


# Campos de texto obrigatórios e opcionais, para os dois validadores de limpeza.
REQUIRED_TEXT_FIELDS = ("code", "name", "type")
OPTIONAL_TEXT_FIELDS = ("manufacturer", "model", "notes", "farm_id", "device_id")


def _require_text(value: str | None) -> str | None:
    """Tira os espaços das pontas e recusa o que sobrar vazio.

    O `min_length=1` do pydantic roda **antes** deste validador, então `"   "` passaria por ele.
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("não pode ficar em branco")
    return stripped


def _optional_text(value: str | None) -> str | None:
    """Tira os espaços das pontas; o que sobrar vazio vira `None`.

    Um formulário devolve `""` para o campo que o usuário não preencheu — e "não preenchido" é
    ausência de valor, não string vazia gravada no banco.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class MachineCreate(BaseModel):
    """Corpo de `POST /api/v1/machines`."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=1,
        max_length=CODE_MAX_LENGTH,
        description="Identidade da máquina (ex.: TR-001). Normalizado para maiúsculas.",
    )
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, description="Nome na tela.")
    type: str = Field(
        min_length=1,
        max_length=TYPE_MAX_LENGTH,
        description="Tipo da máquina (ex.: tractor, harvester).",
    )

    manufacturer: str | None = Field(
        default=None, max_length=BRAND_MAX_LENGTH, description="Fabricante."
    )
    model: str | None = Field(default=None, max_length=BRAND_MAX_LENGTH, description="Modelo.")
    year: int | None = Field(
        default=None,
        ge=MIN_MANUFACTURING_YEAR,
        le=MAX_MANUFACTURING_YEAR,
        description="Ano de fabricação.",
    )

    farm_id: str | None = Field(
        default=None, description="Fazenda do catálogo (W1) a que a máquina pertence."
    )
    device_id: str | None = Field(
        default=None, description="Equipamento do catálogo (W1) instalado nela, se houver."
    )

    base_tilt_limit_deg: float | None = Field(
        default=None,
        gt=MIN_TILT_LIMIT_DEG,
        le=MAX_TILT_LIMIT_DEG,
        description="Limite de inclinação de catálogo da máquina, em graus. **Informativo**: não "
        "altera o limite enviado ao equipamento (regras-de-risco §4).",
    )
    hour_meter_h: float | None = Field(
        default=None, ge=0.0, le=MAX_HOUR_METER_H, description="Horímetro, em horas."
    )
    acquisition_date: dt.date | None = Field(default=None, description="Data de aquisição.")
    notes: str | None = Field(
        default=None,
        max_length=NOTES_MAX_LENGTH,
        description="Observações sobre o equipamento. Nunca dados de pessoas (LGPD).",
    )
    active: bool = Field(default=True, description="Se a máquina está em operação.")

    @field_validator(*REQUIRED_TEXT_FIELDS, mode="after")
    @classmethod
    def clean_required_text(cls, value: str | None) -> str | None:
        return _require_text(value)

    @field_validator(*OPTIONAL_TEXT_FIELDS, mode="after")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value)


class MachineUpdate(BaseModel):
    """Corpo de `PATCH /api/v1/machines/{code}`: edição parcial.

    Todo campo é opcional e o schema distingue **"não informado"** de **"limpar"**:

    - a chave ausente do JSON não entra em `changes()` e o valor gravado não muda;
    - a chave presente com `null` entra em `changes()` com `None` e **apaga** o campo — é assim
      que a tela desvincula um ESP32 (`{"device_id": null}`).

    Quem separa os dois casos é `model_fields_set`, do pydantic, e não uma comparação com `None`.
    Os campos de `NON_CLEARABLE_FIELDS` recusam `null`: sem `code`, `name` ou `type` a máquina
    deixaria de ser identificável.
    """

    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=CODE_MAX_LENGTH)
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    type: str | None = Field(default=None, min_length=1, max_length=TYPE_MAX_LENGTH)

    manufacturer: str | None = Field(default=None, max_length=BRAND_MAX_LENGTH)
    model: str | None = Field(default=None, max_length=BRAND_MAX_LENGTH)
    year: int | None = Field(default=None, ge=MIN_MANUFACTURING_YEAR, le=MAX_MANUFACTURING_YEAR)

    farm_id: str | None = None
    device_id: str | None = None

    base_tilt_limit_deg: float | None = Field(
        default=None, gt=MIN_TILT_LIMIT_DEG, le=MAX_TILT_LIMIT_DEG
    )
    hour_meter_h: float | None = Field(default=None, ge=0.0, le=MAX_HOUR_METER_H)
    acquisition_date: dt.date | None = None
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    active: bool | None = None

    @field_validator(*REQUIRED_TEXT_FIELDS, mode="after")
    @classmethod
    def clean_required_text(cls, value: str | None) -> str | None:
        return _require_text(value)

    @field_validator(*OPTIONAL_TEXT_FIELDS, mode="after")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @model_validator(mode="after")
    def check_clearable_fields(self) -> "MachineUpdate":
        """Recusa `null` explícito nos campos que a máquina não pode perder."""
        for field in NON_CLEARABLE_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"O campo '{field}' não pode ser nulo.")
        return self

    def changes(self) -> dict[str, Any]:
        """Só os campos que vieram no JSON — com `None` onde o cliente pediu para limpar."""
        return self.model_dump(exclude_unset=True)


class MachineResponse(BaseModel):
    """Uma máquina como a listagem devolve."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="Identificador interno da linha.")
    code: str = Field(description="Identidade da máquina (ex.: TR-001).")
    name: str = Field(description="Nome na tela.")
    type: str = Field(description="Tipo da máquina.")

    manufacturer: str | None = Field(default=None, description="Fabricante.")
    model: str | None = Field(default=None, description="Modelo.")
    year: int | None = Field(default=None, description="Ano de fabricação.")

    farm_id: str | None = Field(default=None, description="Fazenda do catálogo (W1).")
    device_id: str | None = Field(default=None, description="ESP32 vinculado, ou nulo.")

    base_tilt_limit_deg: float | None = Field(
        default=None,
        description="Limite de catálogo da máquina, em graus. **Informativo** (regras §4).",
    )
    hour_meter_h: float | None = Field(default=None, description="Horímetro, em horas.")
    acquisition_date: dt.date | None = Field(default=None, description="Data de aquisição.")
    notes: str | None = Field(default=None, description="Observações sobre o equipamento.")
    active: bool = Field(description="Se a máquina está em operação.")

    created_at: dt.datetime = Field(description="Quando foi cadastrada (UTC).")
    updated_at: dt.datetime = Field(description="Última edição (UTC).")


class LinkedDevice(BaseModel):
    """O ESP32 vinculado à máquina: o que o catálogo diz dele e como ele está agora (W5).

    `device.base_tilt_limit_deg` é o `L_ref` que **de fato** entra no limite enviado ao
    equipamento (regras-de-risco §4) — o campo homônimo da máquina é apenas informativo.
    """

    model_config = ConfigDict(extra="forbid")

    device: Device = Field(description="O equipamento como está no catálogo (W1).")
    farm_id: str = Field(description="Fazenda dona do equipamento, no catálogo.")
    farm_name: str = Field(description="Nome dessa fazenda.")
    status: DeviceStatusResponse = Field(description="Estado ao vivo do equipamento (W5).")


class MachineWithDevice(MachineResponse):
    """Uma máquina com o dispositivo vinculado e o estado ao vivo dele.

    `device` é nulo quando a máquina não tem ESP32 — ou quando o `device_id` gravado saiu do
    catálogo depois do cadastro.
    """

    device: LinkedDevice | None = Field(default=None, description="ESP32 vinculado, se houver.")
