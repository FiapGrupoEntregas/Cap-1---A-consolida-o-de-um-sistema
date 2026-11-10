"""Testes das regras de alerta: `cd alerta && uv run pytest -q`."""

from regras import (NUTRIENTE_MINIMO, PH_MAXIMO, PH_MINIMO, UMIDADE_MINIMA, avaliar_deteccao, avaliar_leitura,
                    montar_mensagem)

LEITURA_OK = {"soil_moisture_percent": 70, "ph": 6.4, "nitrogen": 50, "phosphorus": 50, "potassium": 50,
              "air_temperature": 25.0, "air_humidity": 60.0}


def chaves(leitura):
    return [a.chave for a in avaliar_leitura(leitura)]


def test_leitura_normal_nao_gera_alerta():
    assert chaves(LEITURA_OK) == []


def test_limites_exatos_nao_geram_alerta():
    assert chaves({**LEITURA_OK, "soil_moisture_percent": UMIDADE_MINIMA, "ph": PH_MINIMO,
                   "nitrogen": NUTRIENTE_MINIMO}) == []
    assert chaves({**LEITURA_OK, "ph": PH_MAXIMO}) == []


def test_solo_seco():
    alertas = avaliar_leitura({**LEITURA_OK, "soil_moisture_percent": UMIDADE_MINIMA - 1})
    assert [a.chave for a in alertas] == ["solo_seco"]
    assert "irrigação" in alertas[0].acao


def test_ph_acido_e_alcalino():
    assert chaves({**LEITURA_OK, "ph": 5.9}) == ["solo_acido"]
    assert chaves({**LEITURA_OK, "ph": 6.9}) == ["solo_alcalino"]


def test_nutrientes_baixos():
    assert chaves({**LEITURA_OK, "nitrogen": 10}) == ["nitrogen_baixo"]
    assert chaves({**LEITURA_OK, "phosphorus": 0, "potassium": 29}) == ["phosphorus_baixo", "potassium_baixo"]


def test_varios_alertas_na_mesma_leitura():
    assert chaves({"soil_moisture_percent": 20, "ph": 4.5, "nitrogen": 5, "phosphorus": 80, "potassium": 80}) == [
        "solo_seco", "solo_acido", "nitrogen_baixo"]


def test_campos_ausentes_sao_ignorados():
    assert chaves({}) == []
    assert chaves({"ph": None, "soil_moisture_percent": 10}) == ["solo_seco"]


def test_deteccao_de_vaca():
    assert [a.chave for a in avaliar_deteccao({"trator": 1, "vaca": 0})] == []
    assert [a.chave for a in avaliar_deteccao({"trator": 0, "vaca": 2})] == ["animal_na_lavoura"]


def test_mensagem():
    alertas = avaliar_leitura({**LEITURA_OK, "soil_moisture_percent": 30, "ph": 5.0})
    assunto, corpo = montar_mensagem({**LEITURA_OK, "soil_moisture_percent": 30, "ph": 5.0}, alertas,
                                     "teste", "2026-11-08 20:00")
    assert assunto.startswith("[FarmTech] 2 alerta(s)") and len(assunto) <= 100
    assert "Ligar a irrigação" in corpo and "calcário" in corpo and "umidade do solo 30%" in corpo
