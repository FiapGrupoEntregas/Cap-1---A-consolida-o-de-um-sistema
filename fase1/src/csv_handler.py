import os

import pandas as pd
from model.crop import Crop
from dataclasses import asdict, fields

CSV_FILE = 'farm_tech_solutions.csv'
COLUMNS = [field.name for field in fields(Crop)]
CSV_SEPARATOR = ';'

def create_csv_file() -> None:
    if not os.path.exists(CSV_FILE):
        empty_df = pd.DataFrame(columns=COLUMNS)
        empty_df.to_csv(CSV_FILE, index=False, sep=CSV_SEPARATOR)
        print(f"Created new database file: {CSV_FILE}")

def get_all_crops() -> list[Crop]:
    create_csv_file()
    df = pd.read_csv(CSV_FILE, sep=CSV_SEPARATOR)
    crops: list[Crop] = []
    for _, row in df.iterrows():
            crop = Crop(
                id=int(row['id']),
                type=str(row['type']),
                area_type=str(row['area_type']),
                area=float(row['area']),
                input_management=float(row['input_management'])
            )
            crops.append(crop)
            
    return crops

def update_all_crops_in_csv(crops: list[Crop]) -> None:
    """
    Recebe uma lista de objetos Crop e sobrescreve o CSV atual com esses dados.
    """
    # Se a lista estiver vazia, cria um DataFrame vazio com as colunas corretas
    if not crops:
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(CSV_FILE, index=False, sep=CSV_SEPARATOR)
        print(f"Todas as culturas foram removidas. Arquivo CSV limpo.")
        return

    # Converte a lista de dataclasses para uma lista de dicionários
    crop_dicts = []
    for crop in crops:
        crop_dict = asdict(crop)
        # Garante que o UUID seja convertido para string antes de ir para o pandas
        # crop_dict['id'] = str(crop_dict['id'])
        crop_dicts.append(crop_dict)

    # Cria o novo DataFrame e sobrescreve o arquivo CSV
    df = pd.DataFrame(crop_dicts, columns=COLUMNS)
    df.to_csv(CSV_FILE, index=False, sep=CSV_SEPARATOR)
    
    print(f"Arquivo CSV atualizado com sucesso. Total de registros: {len(crops)}")