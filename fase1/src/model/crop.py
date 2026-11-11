from dataclasses import dataclass

@dataclass
class Crop:
    id: int
    type: str
    area_type: str
    area: float
    input_management: float
