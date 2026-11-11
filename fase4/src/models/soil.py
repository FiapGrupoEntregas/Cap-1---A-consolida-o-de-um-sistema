from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SoilData(BaseModel):
    air_humidity: float
    air_temperature: float
    soil_moisture_raw: int
    soil_moisture_percent: int
    ph: float
    nitrogen: int
    phosphorus: int
    potassium: int
    light_raw: int
    light_percent: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SoilDataResponse(SoilData):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
