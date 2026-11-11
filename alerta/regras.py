"""Regras de alerta da FarmTech (funções puras, sem rede nem banco).

Recebem uma leitura da Fase 4 (dicionário com os campos de SOIL_DATA) e devolvem a lista de
alertas, cada um com chave, problema, ação corretiva e o valor medido. Os limites de umidade e pH
são os do firmware da Fase 2 (cultura de referência: tomate). Para N, P e K a Fase 4 envia níveis
de 0 a 100 %, não presente/ausente: adotamos 30 % como mínimo (decisão da Fase 7, registrada em
docs/plano-entrega/04-alerta-aws.md).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

UMIDADE_MINIMA = 60.0      # %  (Fase 2: liga a irrigação abaixo disso)
PH_MINIMO = 6.0            # Fase 2: faixa ideal 6,0 a 6,8
PH_MAXIMO = 6.8
NUTRIENTE_MINIMO = 30      # % do nível do potenciômetro (N, P, K)

NUTRIENTES = {"nitrogen": "nitrogênio (N)", "phosphorus": "fósforo (P)", "potassium": "potássio (K)"}


@dataclass(frozen=True)
class Alerta:
    chave: str          # identifica a condição (usada para não repetir o mesmo alerta em sequência)
    problema: str
    acao: str
    valor: float | int | None = None

    def dict(self) -> dict:
        return asdict(self)


def avaliar_leitura(leitura: dict) -> list[Alerta]:
    """Aplica as regras a uma leitura da Fase 4. Campos ausentes (None) não geram alerta."""
    alertas: list[Alerta] = []

    umidade = leitura.get("soil_moisture_percent")
    if umidade is not None and umidade < UMIDADE_MINIMA:
        alertas.append(Alerta("solo_seco", f"Solo seco: umidade do solo em {umidade:.0f}% (mínimo {UMIDADE_MINIMA:.0f}%)",
                              "Ligar a irrigação do talhão", umidade))

    ph = leitura.get("ph")
    if ph is not None:
        if ph < PH_MINIMO:
            alertas.append(Alerta("solo_acido", f"Solo ácido: pH {ph:.1f} (mínimo {PH_MINIMO:.1f})",
                                  "Aplicar calcário (calagem) para corrigir a acidez", ph))
        elif ph > PH_MAXIMO:
            alertas.append(Alerta("solo_alcalino", f"Solo alcalino: pH {ph:.1f} (máximo {PH_MAXIMO:.1f})",
                                  "Corrigir com enxofre e revisar a adubação", ph))

    for campo, nome in NUTRIENTES.items():
        nivel = leitura.get(campo)
        if nivel is not None and nivel < NUTRIENTE_MINIMO:
            alertas.append(Alerta(f"{campo}_baixo", f"Nível de {nome} baixo: {nivel:.0f}% (mínimo {NUTRIENTE_MINIMO}%)",
                                  f"Adubar com {nome}", nivel))

    return alertas


def avaliar_deteccao(resumo: dict) -> list[Alerta]:
    """Regras sobre o resumo do detect.py da Fase 6 ({"trator": n, "vaca": n})."""
    alertas: list[Alerta] = []
    vacas = resumo.get("vaca", 0)
    if vacas:
        alertas.append(Alerta("animal_na_lavoura", f"Animal na área monitorada: {vacas} vaca(s) detectada(s)",
                              "Verificar as cercas do talhão e afastar o rebanho da lavoura", vacas))
    return alertas


def montar_mensagem(leitura: dict, alertas: list[Alerta], origem: str, quando: str) -> tuple[str, str]:
    """Assunto (até 100 caracteres, limite do SNS) e corpo do e-mail."""
    assunto = f"[FarmTech] {len(alertas)} alerta(s): " + ", ".join(a.chave.replace("_", " ") for a in alertas)
    linhas = [
        "FarmTech Solutions — alerta de monitoramento",
        f"Quando: {quando}",
        f"Origem: {origem}",
        "",
        "Problemas e ações corretivas:",
    ]
    for i, a in enumerate(alertas, 1):
        linhas += [f"  {i}. {a.problema}", f"     Ação: {a.acao}"]
    campos = [("umidade do solo", "soil_moisture_percent", "%"), ("pH", "ph", ""), ("N", "nitrogen", "%"),
              ("P", "phosphorus", "%"), ("K", "potassium", "%"), ("temperatura do ar", "air_temperature", "°C"),
              ("umidade do ar", "air_humidity", "%")]
    medidas = [f"{nome} {leitura[c]}{u}" for nome, c, u in campos if leitura.get(c) is not None]
    if medidas:
        linhas += ["", "Leitura completa: " + "; ".join(medidas)]
    return assunto[:100], "\n".join(linhas)
