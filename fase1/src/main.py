from farm_math_handler import mango_handler, sugar_cane_handler
from input_handler import handle_cultura_input, handle_index
from menus import main_menu 
from csv_handler import get_all_crops, update_all_crops_in_csv
from model.crop import Crop

crops: list[Crop] = []

def list_crops():
    if not crops:
        print("\nNenhum dado cadastrado foi encontrado.")
        return

    print("Lista de Dados:")
    for crop in crops:
        medida_insumo = "L" if crop.area_type == "Retangulo" else "kg"
        print(f'== idx: {crop.id},  Tipo: {crop.type}, Tipo de Area: {crop.area_type}, Área: {crop.area:.2f} m², Total de Insumos: {crop.input_management:.2f} {medida_insumo}')

def delete_crop():
    target_id = handle_index('Qual o ID do dado que você deseja remover?:')
    
    for i, crop in enumerate(crops):
        if crop.id == target_id:
            del crops[i]
            print(f"Cultura com ID {target_id} deletada com sucesso.")
            return
    print(f'[Error]Cultura com ID {target_id} não foi encontrada no sistema.')

def update_crop():
    target_id = handle_index('Qual o ID do dado que você deseja atualizar?\n:')

    crop = next((c for c in crops if c.id == target_id), None)
    
    if not crop:
        print(f'[Error]Cultura com ID {target_id} não encontrada no sistema.')
        return

    type = handle_cultura_input()

    if type == "X":
        print(f"Retornando para menu principal.")
        return

    if type == "1":
        cultura, area_type, area, input_management = mango_handler()
    elif type == "2": 
        cultura, area_type, area, input_management = sugar_cane_handler()
    
    crop.area = area
    crop.area_type = area_type
    crop.type = cultura
    crop.area = area
    crop.input_management = input_management
    

def insert_crop():
    type = handle_cultura_input()

    if type == "X":
        print(f"Retornando para menu principal.")
        return

    if type == "1":
        cultura, area_type, area, input_management = mango_handler()
    elif type == "2": 
        cultura, area_type, area, input_management = sugar_cane_handler()

    nova_cultura = Crop(
        id=max((c.id for c in crops), default=-1) + 1,
        type=cultura,
        area_type=area_type,
        area=area,
        input_management=input_management
    )

    # Adiciona o objeto na lista
    crops.append(nova_cultura)

    print(f"\n[Sucesso] {cultura} registrada com ID: {nova_cultura.id}")

    
if __name__ == "__main__":
    crops = get_all_crops()
    exit = False
    while not exit:
        option = main_menu()
        if option == '1':
            insert_crop()
        elif option == '2':
            list_crops()
        elif option == '3':
            update_crop()
        elif option == '4':
            delete_crop()
        elif option == '5':
            update_all_crops_in_csv(crops)
        elif option == '6':
            update_csv = input("Deseja atualizar csv com dados atuais s/n\n:").strip().lower()
            if update_csv == 's':
                update_all_crops_in_csv(crops)
            print('Programa está finalizando')
            exit = True
        else:
            print(f'[Error]Input {option} não foi definido')


