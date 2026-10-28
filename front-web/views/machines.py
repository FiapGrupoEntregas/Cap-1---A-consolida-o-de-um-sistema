"""Maquinário — cadastro das máquinas e vínculo com o ESP32 (W14).

É a única tela que **escreve** no sistema: cadastra, edita e exclui maquinário. As regras
continuam todas na API — código único, um ESP32 por máquina, coerência entre a fazenda da
máquina e a do dispositivo. Aqui a tela só impede o óbvio (campo obrigatório em branco) e mostra
a mensagem que a API respondeu **ao lado do campo que a causou**.

Distinguir "não mexi" de "limpar" é o cuidado central da edição: o `PATCH` só leva os campos que
mudaram, e um campo que o usuário esvaziou viaja como `null` — é assim que se desvincula um ESP32.
"""

import datetime as dt
from typing import Any

import pandas as pd
import streamlit as st

from components.formatting import event_line, local_time, num
from services.api_client import (
    ApiError,
    ApiKeyError,
    NotFoundError,
    RejectedDataError,
    create_machine,
    delete_machine,
    get_device_history,
    get_device_status,
    get_farm,
    get_latest_telemetry,
    get_machine,
    list_farms,
    list_machines,
    update_machine,
)

# --- chaves de sessão (próprias, nunca a chave de um widget: ver components/state.py) ---

# Máquina aberta no detalhe.
SELECTED_CODE_KEY = "machine_code"
# Erro da última escrita: {"form": prefixo, "field": campo ou None, "message": texto da API}.
FORM_ERROR_KEY = "machine_form_error"
# Aviso a mostrar no topo depois de uma escrita bem-sucedida: (tipo, texto).
FLASH_KEY = "machine_flash"

CREATE_FORM = "create"

# --- opções dos seletores ---

ALL_FARMS = "__all__"
NO_FARM = "__none__"
NO_DEVICE = "__none__"

LINK_FILTERS = {
    "Todas": None,
    "Só com ESP32": True,
    "Só sem ESP32": False,
}

# Campos que a tela não deixa enviar em branco — o único "não" que ela dá sozinha.
REQUIRED_FIELDS = {"code": "o código", "name": "o nome", "type": "o tipo"}

# Limites dos widgets, espelhando `api/app/schemas/machine.py`. São só guarda-corpos de digitação:
# quem valida continua sendo a API, que responde 422 com a mensagem certa.
#
# `MIN_TILT_LIMIT_DEG` é **0,0 de propósito**, e não 0,1: o schema usa `gt=0.0`, então a API aceita
# 0,05. Um `min_value` mais alto que um valor já gravado faz o `st.number_input` levantar
# `StreamlitValueBelowMinError` e **derrubar a página inteira** ao abrir aquela máquina. Recusar o
# zero é trabalho da API, e o 422 dela já aparece ao lado do campo.
CODE_MAX_CHARS = 32
NAME_MAX_CHARS = 120
TYPE_MAX_CHARS = 40
BRAND_MAX_CHARS = 80
NOTES_MAX_CHARS = 500
MIN_YEAR = 1900
MAX_YEAR = 2100
MIN_TILT_LIMIT_DEG = 0.0
MAX_TILT_LIMIT_DEG = 90.0
MAX_HOUR_METER_H = 200_000.0

HISTORY_DAYS = 7
TIMELINE_LIMIT = 5

LGPD_NOTICE = (
    "⚠️ **Sem dados de pessoas.** Escreva sobre o equipamento (manutenção, implemento, pneus). "
    "Nome, CPF, telefone ou matrícula de operador **não** entram aqui (LGPD)."
)

TILT_LIMIT_HELP = (
    "Limite de catálogo da máquina, em graus. É **informativo**: o limite enviado ao equipamento "
    "continua vindo do catálogo e das regras de risco, não deste campo."
)

DEVICE_HELP = (
    "O ESP32 instalado nesta máquina. Cada dispositivo pertence a **uma** máquina — se ele já "
    "estiver em outra, a API recusa e diz qual."
)

# Em que campo desenhar a mensagem que a API mandou. Não é regra de negócio: a recusa e o texto
# são dela; aqui só se escolhe onde o texto aparece. A ordem importa — a recusa por fazenda
# diferente fala das duas coisas e pertence ao campo do dispositivo. O que não casar com nada
# aparece no topo do formulário, então nenhuma mensagem se perde.
MESSAGE_FIELDS = (
    ("código", "code"),
    ("equipamento", "device_id"),
    ("fazenda", "farm_id"),
)


# ---------------------------------------------------------------- estado da tela


def _remember_error(form: str, message: str, field: str | None = None) -> None:
    """Guarda o erro da escrita para a próxima passada desenhar no lugar certo."""
    st.session_state[FORM_ERROR_KEY] = {"form": form, "field": field, "message": message}


def _forget_error() -> None:
    st.session_state.pop(FORM_ERROR_KEY, None)


def _drop_orphan_error() -> None:
    """Descarta o erro cujo formulário perdeu o estado na troca de página.

    `FORM_ERROR_KEY` é chave própria e atravessa a navegação, mas os campos (chaves de widget) não
    — é o comportamento documentado em `components/state.py`. Sem isso, sair da página depois de um
    409 e voltar reabre a tela com uma mensagem vermelha embaixo de um formulário **vazio**.
    """
    error = st.session_state.get(FORM_ERROR_KEY)
    if not error:
        return
    prefix = f"{error['form']}_"
    if not any(key.startswith(prefix) for key in st.session_state):
        _forget_error()


def _flash(kind: str, message: str) -> None:
    st.session_state[FLASH_KEY] = (kind, message)


def _show_flash() -> None:
    """Mostra (uma vez) o aviso da última escrita."""
    flash = st.session_state.pop(FLASH_KEY, None)
    if not flash:
        return
    kind, message = flash
    (st.success if kind == "success" else st.info)(message)


def _clear_widget_state(prefix: str) -> None:
    """Esquece os campos de um formulário, para ele não reabrir com o que já foi enviado."""
    for key in [key for key in st.session_state if key.startswith(f"{prefix}_")]:
        del st.session_state[key]


def _error_field(error: RejectedDataError) -> str | None:
    """Campo a que a recusa se refere: o que o pydantic apontou ou o que a frase menciona."""
    if error.fields:
        return error.fields[0]
    message = error.message.lower()
    for token, field in MESSAGE_FIELDS:
        if token in message:
            return field
    return None


def _form_has_error(form: str) -> bool:
    """O expander deste formulário precisa abrir sozinho?

    Todo envio termina em `st.rerun()`, e a mensagem de erro vive **dentro** do expander. Sem
    `expanded=`, a visibilidade dependeria de o Streamlit preservar o expander aberto entre
    reruns — o que o `AppTest` não valida e o palco não perdoa. O sucesso já aparece no topo, por
    `_show_flash()`; isto torna o erro igualmente determinístico.
    """
    error = st.session_state.get(FORM_ERROR_KEY)
    return bool(error and error["form"] == form)


def _field_error(form: str, field: str) -> None:
    """Desenha, logo abaixo do campo, a mensagem da API que se refere a ele."""
    error = st.session_state.get(FORM_ERROR_KEY)
    if error and error["form"] == form and error["field"] == field:
        st.error(error["message"], icon="🚫")


def _form_error_banner(form: str) -> None:
    """Erros que não pertencem a um campo (chave de API, API fora do ar, obrigatório em branco)."""
    error = st.session_state.get(FORM_ERROR_KEY)
    if error and error["form"] == form and not error["field"]:
        st.error(error["message"], icon="🚫")


# ---------------------------------------------------------------- catálogo (W1)


def _load_farms() -> list[dict] | None:
    """Fazendas do catálogo, para os filtros e os seletores. `None` quando a API não responde."""
    try:
        return list_farms()
    except ApiError as error:
        st.error(str(error))
        return None


def _load_devices(farms: list[dict]) -> list[dict]:
    """Equipamentos de todas as fazendas do catálogo, para o seletor de vínculo.

    A lista completa é de propósito: quem diz se o ESP32 combina com a fazenda da máquina é a
    API (ela responde 422 quando são de fazendas diferentes), não um filtro feito aqui.
    """
    devices: list[dict] = []
    for farm in farms:
        try:
            detail = get_farm(farm["id"])
        except ApiError:
            continue  # uma fazenda sem detalhe não impede cadastrar as outras
        for device in detail.get("devices") or []:
            devices.append({**device, "farm_id": farm["id"], "farm_name": farm["name"]})
    return devices


def _farm_names(farms: list[dict]) -> dict[str, str]:
    return {farm["id"]: farm["name"] for farm in farms}


# ---------------------------------------------------------------- listagem


def _machines_frame(machines: list[dict], farm_names: dict[str, str]) -> pd.DataFrame:
    """A frota como tabela. 🟢 tem ESP32 vinculado, ⚫ não tem."""
    rows = []
    for machine in machines:
        device_id = machine.get("device_id")
        farm_id = machine.get("farm_id")
        rows.append(
            {
                "Código": machine["code"],
                "Nome": machine["name"],
                "Tipo": machine["type"],
                "Fabricante": machine.get("manufacturer") or "—",
                "Modelo": machine.get("model") or "—",
                "Ano": str(machine["year"]) if machine.get("year") else "—",
                "Fazenda": farm_names.get(farm_id, farm_id or "—"),
                "ESP32": f"🟢 {device_id}" if device_id else "⚫ sem vínculo",
                "Em operação": "sim" if machine.get("active") else "não",
            }
        )
    return pd.DataFrame(rows)


def _render_filters(farms: list[dict]) -> tuple[str | None, bool | None]:
    farm_column, link_column = st.columns(2)
    farm_ids = [ALL_FARMS, *[farm["id"] for farm in farms]]
    names = _farm_names(farms)
    with farm_column:
        chosen_farm = st.selectbox(
            "Fazenda",
            farm_ids,
            format_func=lambda farm_id: (
                "Todas as fazendas" if farm_id == ALL_FARMS else names.get(farm_id, farm_id)
            ),
        )
    with link_column:
        chosen_link = st.selectbox("Vínculo com ESP32", list(LINK_FILTERS))
    return (None if chosen_farm == ALL_FARMS else chosen_farm), LINK_FILTERS[chosen_link]


# ---------------------------------------------------------------- campos do formulário


def _text_field(
    label: str, form: str, field: str, machine: dict, max_chars: int, help_text: str | None = None
) -> str | None:
    """Campo de texto: o que ficar vazio vira `None` (ausência de valor, não string vazia)."""
    value = st.text_input(
        label,
        value=machine.get(field) or "",
        max_chars=max_chars,
        key=f"{form}_{field}",
        help=help_text,
    )
    _field_error(form, field)
    return value.strip() or None


def _number_field(label: str, form: str, field: str, machine: dict, **kwargs: Any) -> Any:
    """Campo numérico opcional: vazio é `None` e, na edição, `None` significa limpar."""
    value = st.number_input(label, value=machine.get(field), key=f"{form}_{field}", **kwargs)
    _field_error(form, field)
    return value


def _farm_field(form: str, machine: dict, farms: list[dict]) -> str | None:
    names = _farm_names(farms)
    options = [NO_FARM, *names]
    current = machine.get("farm_id") or NO_FARM
    if current not in options:
        options.append(current)  # fazenda que saiu do catálogo continua visível
    chosen = st.selectbox(
        "Fazenda",
        options,
        index=options.index(current),
        format_func=lambda farm_id: (
            "— sem fazenda —" if farm_id == NO_FARM else names.get(farm_id, farm_id)
        ),
        key=f"{form}_farm_id",
    )
    _field_error(form, "farm_id")
    return None if chosen == NO_FARM else chosen


def _device_field(form: str, machine: dict, devices: list[dict]) -> str | None:
    labels = {
        device["device_id"]: f"{device['device_id']} — {device['name']} ({device['farm_name']})"
        for device in devices
    }
    options = [NO_DEVICE, *labels]
    current = machine.get("device_id") or NO_DEVICE
    if current not in options:
        options.append(current)  # vínculo com um dispositivo que saiu do catálogo
    chosen = st.selectbox(
        "ESP32 vinculado",
        options,
        index=options.index(current),
        format_func=lambda device_id: (
            "— sem vínculo —" if device_id == NO_DEVICE else labels.get(device_id, device_id)
        ),
        help=DEVICE_HELP,
        key=f"{form}_device_id",
    )
    _field_error(form, "device_id")
    return None if chosen == NO_DEVICE else chosen


def _date_field(form: str, machine: dict) -> str | None:
    raw = machine.get("acquisition_date")
    try:
        current = dt.date.fromisoformat(raw) if raw else None
    except ValueError:
        current = None
    chosen = st.date_input(
        "Data de aquisição",
        value=current,
        format="DD/MM/YYYY",
        key=f"{form}_acquisition_date",
    )
    _field_error(form, "acquisition_date")
    return chosen.isoformat() if isinstance(chosen, dt.date) else None


def _machine_fields(form: str, machine: dict, farms: list[dict], devices: list[dict]) -> dict:
    """Desenha os campos do cadastro e devolve os valores prontos para virar JSON."""
    values: dict[str, Any] = {}

    first, second, third = st.columns(3)
    with first:
        values["code"] = _text_field(
            "Código *",
            form,
            "code",
            machine,
            CODE_MAX_CHARS,
            "A identidade da máquina, como TR-001. A API guarda em maiúsculas.",
        )
    with second:
        values["name"] = _text_field("Nome *", form, "name", machine, NAME_MAX_CHARS)
    with third:
        values["type"] = _text_field(
            "Tipo *", form, "type", machine, TYPE_MAX_CHARS, "Ex.: tractor, harvester, sprayer."
        )

    fourth, fifth, sixth = st.columns(3)
    with fourth:
        values["manufacturer"] = _text_field(
            "Fabricante", form, "manufacturer", machine, BRAND_MAX_CHARS
        )
    with fifth:
        values["model"] = _text_field("Modelo", form, "model", machine, BRAND_MAX_CHARS)
    with sixth:
        values["year"] = _number_field(
            "Ano de fabricação",
            form,
            "year",
            machine,
            min_value=MIN_YEAR,
            max_value=MAX_YEAR,
            step=1,
            format="%d",
            placeholder="opcional",
        )

    seventh, eighth = st.columns(2)
    with seventh:
        values["farm_id"] = _farm_field(form, machine, farms)
    with eighth:
        values["device_id"] = _device_field(form, machine, devices)

    ninth, tenth, eleventh = st.columns(3)
    with ninth:
        values["base_tilt_limit_deg"] = _number_field(
            "Limite de inclinação de catálogo (°)",
            form,
            "base_tilt_limit_deg",
            machine,
            min_value=MIN_TILT_LIMIT_DEG,
            max_value=MAX_TILT_LIMIT_DEG,
            step=0.5,
            placeholder="opcional",
            help=TILT_LIMIT_HELP,
        )
    with tenth:
        values["hour_meter_h"] = _number_field(
            "Horímetro (h)",
            form,
            "hour_meter_h",
            machine,
            min_value=0.0,
            max_value=MAX_HOUR_METER_H,
            step=10.0,
            placeholder="opcional",
        )
    with eleventh:
        values["acquisition_date"] = _date_field(form, machine)

    values["notes"] = _text_area(form, machine)
    values["active"] = st.checkbox(
        "Máquina em operação", value=bool(machine.get("active", True)), key=f"{form}_active"
    )
    return values


def _text_area(form: str, machine: dict) -> str | None:
    value = st.text_area(
        "Observações",
        value=machine.get("notes") or "",
        max_chars=NOTES_MAX_CHARS,
        key=f"{form}_notes",
        help=LGPD_NOTICE,
    )
    st.caption(LGPD_NOTICE)
    _field_error(form, "notes")
    return value.strip() or None


def _missing_required(values: dict) -> str | None:
    """Primeiro campo obrigatório em branco, se houver."""
    return next((field for field in REQUIRED_FIELDS if not values.get(field)), None)


# ---------------------------------------------------------------- cadastro


def _render_create_form(farms: list[dict], devices: list[dict]) -> None:
    with (
        st.expander("➕ Cadastrar máquina", expanded=_form_has_error(CREATE_FORM)),
        st.form(CREATE_FORM),
    ):
        _form_error_banner(CREATE_FORM)
        values = _machine_fields(CREATE_FORM, {}, farms, devices)
        submitted = st.form_submit_button("Cadastrar", type="primary")

    if submitted:
        _create(values)


def _create(values: dict) -> None:
    missing = _missing_required(values)
    if missing:
        _remember_error(CREATE_FORM, f"Preencha {REQUIRED_FIELDS[missing]}.", field=missing)
        st.rerun()

    # No cadastro, campo vazio é campo **não informado**: ele simplesmente não vai no JSON.
    payload = {field: value for field, value in values.items() if value is not None}
    try:
        created = create_machine(payload)
    except RejectedDataError as error:
        _remember_error(CREATE_FORM, error.message, field=_error_field(error))
    except (ApiKeyError, ApiError) as error:
        _remember_error(CREATE_FORM, str(error))
    else:
        _forget_error()
        _clear_widget_state(CREATE_FORM)
        st.session_state[SELECTED_CODE_KEY] = created["code"]
        _flash("success", f"Máquina **{created['code']}** cadastrada.")
    st.rerun()


# ---------------------------------------------------------------- edição


def _changes(machine: dict, values: dict) -> dict:
    """O que o usuário mexeu — e **só** isso.

    Campo fora do dicionário: o `PATCH` não o menciona e a API não muda nada nele. Campo com
    `None`: a API **limpa** o valor. É a diferença entre "não mexi" e "quero apagar", e é assim
    que a tela desvincula um ESP32 (`{"device_id": None}`).
    """
    return {field: value for field, value in values.items() if value != machine.get(field)}


def _render_edit_form(machine: dict, farms: list[dict], devices: list[dict]) -> None:
    form = f"edit_{machine['code']}"
    with st.expander("✏️ Editar", expanded=_form_has_error(form)), st.form(form):
        _form_error_banner(form)
        values = _machine_fields(form, machine, farms, devices)
        st.caption(
            "Só os campos alterados são enviados. Esvaziar um campo (ou escolher "
            "*— sem vínculo —*) apaga o valor guardado."
        )
        submitted = st.form_submit_button("Salvar alterações", type="primary")

    if submitted:
        _update(machine, form, values)


def _update(machine: dict, form: str, values: dict) -> None:
    missing = _missing_required(values)
    if missing:
        _remember_error(form, f"Preencha {REQUIRED_FIELDS[missing]}.", field=missing)
        st.rerun()

    changes = _changes(machine, values)
    if not changes:
        _forget_error()
        _flash("info", "Nada para salvar: nenhum campo mudou.")
        st.rerun()

    try:
        updated = update_machine(machine["code"], changes)
    except RejectedDataError as error:
        _remember_error(form, error.message, field=_error_field(error))
    except (ApiKeyError, ApiError) as error:
        _remember_error(form, str(error))
    else:
        _forget_error()
        _clear_widget_state(form)
        st.session_state[SELECTED_CODE_KEY] = updated["code"]
        _flash("success", f"Máquina **{updated['code']}** atualizada.")
    st.rerun()


# ---------------------------------------------------------------- exclusão


def _render_delete_block(machine: dict) -> None:
    code = machine["code"]
    form = f"delete_{code}"
    with st.expander("🗑️ Excluir", expanded=_form_has_error(form)):
        st.warning(
            "Excluir apaga **o cadastro**, não a telemetria nem os eventos do ESP32: eles são do "
            "dispositivo e continuam no histórico. O que se desfaz é o vínculo.",
            icon="⚠️",
        )
        typed = st.text_input(
            f"Para confirmar, digite o código `{code}`",
            key=f"{form}_confirmation",
            placeholder=code,
        )
        confirmed = typed.strip().upper() == code.upper()
        _form_error_banner(form)
        if st.button(
            "Excluir definitivamente",
            type="primary",
            disabled=not confirmed,
            key=f"{form}_button",
        ):
            _delete(machine, form, confirmed)


def _delete(machine: dict, form: str, confirmed: bool) -> None:
    if not confirmed:
        # Cinto e suspensório: o botão já fica desabilitado até o código bater.
        _remember_error(form, "O código digitado não confere. Nada foi excluído.")
        st.rerun()

    try:
        delete_machine(machine["code"])
    except (ApiKeyError, RejectedDataError, ApiError) as error:
        _remember_error(form, str(error))
    else:
        _forget_error()
        _clear_widget_state(form)
        st.session_state.pop(SELECTED_CODE_KEY, None)
        _flash("success", f"Máquina **{machine['code']}** excluída.")
    st.rerun()


# ---------------------------------------------------------------- ESP32 vinculado


def _status_line(status: dict) -> str:
    online = status.get("state") == "online"
    silence = status.get("seconds_since_last_telemetry")
    if online:
        line = "🟢 **Online**"
        if silence is not None:
            line += f" · última leitura há {num(silence, 0)} s"
        return line
    line = "⚫ **Offline**"
    if silence is not None:
        line += f" há {num(silence, 0)} s sem telemetria"
    elif status.get("last_seen_at") is None:
        line += " · nunca se conectou"
    return line


def _render_telemetry(device_id: str) -> None:
    try:
        telemetry = get_latest_telemetry(device_id)
    except NotFoundError:
        st.info(
            "Este ESP32 ainda não publicou telemetria. Assim que ele conectar, os números "
            "aparecem aqui.",
            icon="⏳",
        )
        return
    except ApiError as error:
        st.error(str(error))
        return

    roll, pitch, limit = st.columns(3)
    roll.metric("Rolagem (roll)", f"{num(telemetry['roll_deg'])}°")
    pitch.metric("Arfagem (pitch)", f"{num(telemetry['pitch_deg'])}°")
    limit.metric("Limite no equipamento", f"{num(telemetry['tilt_limit_deg'])}°")
    st.caption(f"Última leitura às {local_time(telemetry['ts'])} (seq {telemetry['seq']}).")


def _render_history(device_id: str) -> None:
    try:
        history = get_device_history(device_id, days=HISTORY_DAYS)
    except ApiError as error:
        st.error(str(error))
        return

    st.markdown(f"**Histórico dos últimos {history['days']} dias**")
    hours, above, alerts, rollovers = st.columns(4)
    hours.metric("Horas operando", f"{num(history['operating_hours'])} h")
    above.metric("Tempo acima do limite", f"{num(history['pct_time_above_limit'])}%")
    alerts.metric("Alertas de inclinação", f"{history['alerts']}")
    rollovers.metric("Capotamentos", f"{history['rollovers']}")

    timeline = history.get("timeline") or []
    if not timeline:
        st.caption("Sem eventos registrados no período.")
        return
    for event in timeline[:TIMELINE_LIMIT]:
        st.markdown(event_line(event))


def _render_device_section(machine: dict) -> None:
    device_id = machine.get("device_id")
    linked = machine.get("device")
    if not device_id:
        st.info(
            "Sem ESP32 vinculado. Use **Editar** para escolher um dispositivo do catálogo.",
            icon="📡",
        )
        return
    if not linked:
        st.warning(
            f"O dispositivo `{device_id}` está gravado nesta máquina, mas não aparece mais no "
            "catálogo de fazendas. Verifique o cadastro.",
            icon="⚠️",
        )
        return

    device = linked["device"]
    st.markdown(
        f"📡 **{device['name']}** · `{device['device_id']}` · {linked['farm_name']} · "
        f"limite de catálogo {num(device['base_tilt_limit_deg'])}° em solo seco"
    )

    try:
        status = get_device_status(device_id)
    except ApiError as error:
        st.warning(f"{error} Mostrando o estado que veio com o cadastro.")
        status = linked["status"]
    st.markdown(_status_line(status))

    _render_telemetry(device_id)
    _render_history(device_id)
    st.caption(
        "O painel que se atualiza sozinho, com gráfico e eventos em tempo real, está na página "
        "**Equipamento ao vivo**."
    )


# ---------------------------------------------------------------- detalhe


def _render_detail(machine: dict, farms: list[dict], devices: list[dict]) -> None:
    names = _farm_names(farms)
    farm_id = machine.get("farm_id")
    st.subheader(f"{machine['code']} — {machine['name']}")

    first, second, third, fourth = st.columns(4)
    first.metric("Tipo", machine["type"])
    first.metric("Em operação", "sim" if machine.get("active") else "não")
    second.metric("Fabricante", machine.get("manufacturer") or "—")
    second.metric("Modelo", machine.get("model") or "—")
    third.metric("Ano", str(machine["year"]) if machine.get("year") else "—")
    hour_meter = machine.get("hour_meter_h")
    third.metric("Horímetro", f"{num(hour_meter)} h" if hour_meter is not None else "—")
    fourth.metric("Fazenda", names.get(farm_id, farm_id or "—"))
    tilt_limit = machine.get("base_tilt_limit_deg")
    fourth.metric(
        "Limite de catálogo",
        f"{num(tilt_limit)}°" if tilt_limit is not None else "—",
        help=TILT_LIMIT_HELP,
    )

    acquired = machine.get("acquisition_date")
    if acquired:
        st.caption(f"Adquirida em {dt.date.fromisoformat(acquired).strftime('%d/%m/%Y')}.")
    if machine.get("notes"):
        st.markdown(f"**Observações:** {machine['notes']}")

    _render_device_section(machine)
    _render_edit_form(machine, farms, devices)
    _render_delete_block(machine)


def _open_machine(machines: list[dict]) -> dict | None:
    """Seletor da máquina aberta no detalhe. A escolha fica numa chave própria da sessão."""
    codes = [machine["code"] for machine in machines]
    names = {machine["code"]: machine["name"] for machine in machines}
    saved = st.session_state.get(SELECTED_CODE_KEY)
    index = codes.index(saved) if saved in codes else 0
    chosen = st.selectbox(
        "Abrir máquina",
        codes,
        index=index,
        format_func=lambda code: f"{code} — {names[code]}",
    )
    st.session_state[SELECTED_CODE_KEY] = chosen

    try:
        return get_machine(chosen)
    except NotFoundError:
        st.session_state.pop(SELECTED_CODE_KEY, None)
        st.info("Esta máquina não está mais cadastrada. Atualize a página.", icon="ℹ️")
    except ApiError as error:
        st.error(str(error))
    return None


# ---------------------------------------------------------------- página


st.title("🚜 Maquinário")
st.caption(
    "Cadastro das máquinas da frota e o vínculo com o ESP32 instalado nelas. O cadastro descreve "
    "o **equipamento** — nunca pessoas."
)

_drop_orphan_error()
_show_flash()

catalog_farms = _load_farms()
if catalog_farms is None:
    st.warning(
        "Sem o catálogo de fazendas não dá para cadastrar nem filtrar maquinário. Suba a API "
        "(`uv run fastapi dev app/main.py` na pasta api/) e recarregue a página.",
        icon="⚠️",
    )
    st.stop()

catalog_devices = _load_devices(catalog_farms)

st.subheader("Frota cadastrada")
farm_filter, linked_filter = _render_filters(catalog_farms)

try:
    fleet = list_machines(farm_id=farm_filter, linked=linked_filter)
except ApiError as list_error:
    st.error(str(list_error))
    st.stop()

if fleet:
    st.dataframe(
        _machines_frame(fleet, _farm_names(catalog_farms)), hide_index=True, width="stretch"
    )
    st.caption(
        "🟢 com ESP32 vinculado · ⚫ sem vínculo. O estado **online/offline** do dispositivo "
        "aparece ao abrir a máquina."
    )
else:
    st.info("Nenhuma máquina cadastrada com esses filtros.", icon="🔎")

_render_create_form(catalog_farms, catalog_devices)

if fleet:
    st.divider()
    opened = _open_machine(fleet)
    if opened is not None:
        _render_detail(opened, catalog_farms, catalog_devices)
