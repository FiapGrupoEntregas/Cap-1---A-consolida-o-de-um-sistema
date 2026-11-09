"""
========================================================
 FARMTECH SOLUTIONS - Previsão Climática (Open-Meteo)
========================================================
 API pública gratuita e SEM necessidade de API Key.
 Documentação: https://open-meteo.com/en/docs

 Retorna um código de 1 caractere para o ESP32:
   S = Seco        → irrigação normal
   L = Chuva Leve  → irrigação reduzida
   C = Chuva Forte → suspender irrigação
========================================================
"""

import requests
import sys

# ========== CONFIGURAÇÃO ==========
# Coordenadas (exemplo: São Paulo, SP)
LATITUDE  = -23.5505
LONGITUDE = -46.6333
CIDADE    = "São Paulo, SP"

URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}&longitude={LONGITUDE}"
    f"&hourly=precipitation,rain,precipitation_probability"
    f"&forecast_days=1"
    f"&timezone=America%2FSao_Paulo"
)

def consultar_previsao():
    try:
        print(f"\n>> Consultando Open-Meteo para {CIDADE}...")
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        dados = response.json()

        precipitacoes  = dados["hourly"]["precipitation"][:24]
        probabilidades = dados["hourly"]["precipitation_probability"][:24]

        # Estatísticas
        chuva_total   = sum(precipitacoes)
        chuva_max     = max(precipitacoes)
        prob_max      = max(probabilidades)
        prob_media    = sum(probabilidades) / len(probabilidades)

        print("=" * 55)
        print(f"  FARMTECH - Previsão 24h ({CIDADE})")
        print("=" * 55)
        print(f"  Precipitação total prevista: {chuva_total:.2f} mm")
        print(f"  Pico de precipitação:        {chuva_max:.2f} mm/h")
        print(f"  Probabilidade máx. de chuva: {prob_max}%")
        print(f"  Probabilidade média:         {prob_media:.1f}%")
        print("-" * 55)

        if chuva_total >= 10.0 or chuva_max >= 4.0 or prob_max >= 80:
            codigo = "C"
            msg = "CHUVA FORTE → Suspender irrigação"
        elif chuva_total >= 2.0 or prob_media >= 40:
            codigo = "L"
            msg = "CHUVA LEVE → Irrigação reduzida"
        else:
            codigo = "S"
            msg = "SECO → Irrigação normal"

        print(f"  >> Situação: {msg}")
        print(f"  >> Código para ESP32: [ {codigo} ]")
        print("=" * 55)
        print("\nCopie o caractere acima e cole no Monitor Serial")
        print("do Wokwi (depois aperte Enter).\n")

        return codigo

    except Exception as e:
        print(f"Erro ao consultar API: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 55)
    consultar_previsao()