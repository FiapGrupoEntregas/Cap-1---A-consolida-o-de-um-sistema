import math

from input_handler import handle_float_input, handle_int_input

def calculate_mango_area(length, width):
    return length * width

def calculate_sugar_cane_area(r):
    return math.pi * (r ** 2)

def mango_handler():
    cultura = "Manga"
    area_type = "Retangulo"
    width = handle_float_input("Largura do terreno (m): ")
    length = handle_float_input("Comprimento do terreno (m): ")
    street = handle_int_input("Quantidade de ruas: ")
    liters_per_meter = float(input("Quantidade de litros por metro linear (L/m): "))
    
    area = calculate_mango_area(length, width)
    input_management = street * length * liters_per_meter
    return cultura, area_type, area, input_management


def sugar_cane_handler():
    cultura = "Cana"
    area_type = "Circulo"
    r = handle_float_input("Raio do pivó (m): ")
    fertilizer_kg_by_m2 = handle_float_input("Quantidade de fertilizante por kg/m^2: ")
    area = calculate_sugar_cane_area(r)
    input_management = area * fertilizer_kg_by_m2
    return cultura, area_type, area, input_management