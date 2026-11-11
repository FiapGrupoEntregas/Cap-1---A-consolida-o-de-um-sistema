def handle_index(message: str) -> int:
    index = input(message).strip()
    
    if not index.isdigit():
        print(f'[Error] ID "{index}" não é um número válido.')
        return
    target_id = int(index)
    return target_id

def handle_int_input(message: str) -> int:
    while True:
        value = input(message).strip()
        if value.isdigit():
            return int(value)
        else:
            print(f'[Error] "{value}" não é um número válido. Por favor, tente novamente.')

def handle_float_input(message: str) -> float:
    while True:
        value = input(message).strip()
        try:
            return float(value)
        except ValueError:
            print(f'[Error] "{value}" não é um número válido. Por favor, tente novamente.')

def handle_cultura_input() -> str:
    while True:
        print("== Tipo de cultura ==")
        print("1. Manga")
        print("2. Cana")
        cultura = input("Insira (1/2) ou X para voltar: ").strip().capitalize()
        
        if cultura in ["1", "2", "X"]:
            return cultura
        else:
            print(f'[Error] Cultura inválida. Por favor, digite "1" para Manga ou "2" para Cana.\n')
