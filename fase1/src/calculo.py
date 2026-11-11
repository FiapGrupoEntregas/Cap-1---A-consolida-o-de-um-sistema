"""Fase 1 sem perguntas: calcula área e insumos a partir de argumentos e devolve JSON.

Criado na Fase 7 para a dashboard e o main.py da raiz dispararem o cálculo da Fase 1 sem o menu
interativo. Reutiliza as fórmulas de farm_math_handler.py e, com --salvar, grava no mesmo CSV.

    uv run python calculo.py --cultura manga --largura 100 --comprimento 200 --ruas 10 --litros-por-metro 0.5
    uv run python calculo.py --cultura cana --raio 50 --kg-por-m2 0.2 --salvar
"""

import argparse
import json
import sys

from csv_handler import get_all_crops, update_all_crops_in_csv
from farm_math_handler import calculate_mango_area, calculate_sugar_cane_area
from model.crop import Crop


def calcular(args: argparse.Namespace) -> dict:
    if args.cultura == "manga":
        faltam = [n for n in ("largura", "comprimento", "ruas", "litros_por_metro") if getattr(args, n) is None]
        if faltam:
            sys.exit(f"Para manga informe: {', '.join('--' + f.replace('_', '-') for f in faltam)}")
        area = calculate_mango_area(args.comprimento, args.largura)
        insumo = args.ruas * args.comprimento * args.litros_por_metro
        return {"cultura": "Manga", "tipo_area": "Retangulo", "area_m2": round(area, 2),
                "insumo": round(insumo, 2), "unidade_insumo": "L",
                "entrada": {"largura_m": args.largura, "comprimento_m": args.comprimento,
                            "ruas": args.ruas, "litros_por_metro": args.litros_por_metro}}
    faltam = [n for n in ("raio", "kg_por_m2") if getattr(args, n) is None]
    if faltam:
        sys.exit(f"Para cana informe: {', '.join('--' + f.replace('_', '-') for f in faltam)}")
    area = calculate_sugar_cane_area(args.raio)
    insumo = area * args.kg_por_m2
    return {"cultura": "Cana", "tipo_area": "Circulo", "area_m2": round(area, 2),
            "insumo": round(insumo, 2), "unidade_insumo": "kg",
            "entrada": {"raio_m": args.raio, "kg_por_m2": args.kg_por_m2}}


def salvar(resultado: dict) -> int:
    crops = get_all_crops()
    novo = Crop(id=max((c.id for c in crops), default=-1) + 1, type=resultado["cultura"],
                area_type=resultado["tipo_area"], area=resultado["area_m2"], input_management=resultado["insumo"])
    crops.append(novo)
    update_all_crops_in_csv(crops)
    return novo.id


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Calcula área de plantio e insumos (Fase 1) sem perguntas.")
    p.add_argument("--cultura", required=True, choices=["manga", "cana"])
    p.add_argument("--largura", type=float, help="manga: largura do terreno (m)")
    p.add_argument("--comprimento", type=float, help="manga: comprimento do terreno (m)")
    p.add_argument("--ruas", type=int, help="manga: quantidade de ruas")
    p.add_argument("--litros-por-metro", type=float, help="manga: litros por metro linear (L/m)")
    p.add_argument("--raio", type=float, help="cana: raio do pivô (m)")
    p.add_argument("--kg-por-m2", type=float, help="cana: fertilizante por m² (kg/m²)")
    p.add_argument("--salvar", action="store_true", help="grava o registro em farm_tech_solutions.csv")
    args = p.parse_args(argv)

    resultado = calcular(args)
    if args.salvar:
        resultado["id_csv"] = salvar(resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
