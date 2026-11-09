import math
import os
import random
from datetime import datetime, timedelta
from typing import List

import oracledb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from models import SoilData, SoilDataResponse

load_dotenv()

DB_USER = os.getenv("ORACLE_USER")
DB_PASSWORD = os.getenv("ORACLE_PASSWORD")
DB_DSN = os.getenv("ORACLE_DSN")


def get_db_connection():
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)


app = FastAPI()


@app.post("/soil")
def create_soil_data(data: SoilData):
    now = datetime.now()
    payload = data.model_dump()
    payload["created_at"] = now
    payload["updated_at"] = now

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO soil_data (
                        air_humidity,
                        air_temperature,
                        soil_moisture_raw,
                        soil_moisture_percent,
                        ph,
                        nitrogen,
                        phosphorus,
                        potassium,
                        light_raw,
                        light_percent,
                        latitude,
                        longitude,
                        created_at,
                        updated_at
                    ) VALUES (
                        :air_humidity,
                        :air_temperature,
                        :soil_moisture_raw,
                        :soil_moisture_percent,
                        :ph,
                        :nitrogen,
                        :phosphorus,
                        :potassium,
                        :light_raw,
                        :light_percent,
                        :latitude,
                        :longitude,
                        :created_at,
                        :updated_at
                    )
                    """,
                    payload,
                )
            connection.commit()
    except oracledb.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"message": "Dados inseridos com sucesso"}


@app.get("/soil", response_model=List[SoilDataResponse])
def list_soil_data(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        air_humidity,
                        air_temperature,
                        soil_moisture_raw,
                        soil_moisture_percent,
                        ph,
                        nitrogen,
                        phosphorus,
                        potassium,
                        light_raw,
                        light_percent,
                        latitude,
                        longitude,
                        created_at,
                        updated_at
                    FROM soil_data
                    ORDER BY id DESC
                    OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
                    """,
                    {"offset": offset, "limit": limit},
                )
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
    except oracledb.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return results


@app.get("/soil/{soil_id}", response_model=SoilDataResponse)
def get_soil_data(soil_id: int):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        air_humidity,
                        air_temperature,
                        soil_moisture_raw,
                        soil_moisture_percent,
                        ph,
                        nitrogen,
                        phosphorus,
                        potassium,
                        light_raw,
                        light_percent,
                        latitude,
                        longitude,
                        created_at,
                        updated_at
                    FROM soil_data
                    WHERE id = :soil_id
                    """,
                    {"soil_id": soil_id},
                )
                row = cursor.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Registro não encontrado")
                columns = [col[0].lower() for col in cursor.description]
                result = dict(zip(columns, row))
    except oracledb.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result


@app.get("/soil/month/{year}/{month}", response_model=List[SoilDataResponse])
def list_soil_data_by_month(
    year: int,
    month: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        air_humidity,
                        air_temperature,
                        soil_moisture_raw,
                        soil_moisture_percent,
                        ph,
                        nitrogen,
                        phosphorus,
                        potassium,
                        light_raw,
                        light_percent,
                        latitude,
                        longitude,
                        created_at,
                        updated_at
                    FROM soil_data
                    WHERE EXTRACT(YEAR FROM created_at) = :year
                      AND EXTRACT(MONTH FROM created_at) = :month
                    ORDER BY id DESC
                    OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
                    """,
                    {"year": year, "month": month, "offset": offset, "limit": limit},
                )
                rows = cursor.fetchall()
                columns = [col[0].lower() for col in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
    except oracledb.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return results


def _generate_correlated_record(index: int, base_time: datetime):
    """Gera um registro de solo com correlações realistas entre sensores."""
    hour = index % 24
    daylight = max(0, math.sin((hour - 6) / 12 * math.pi))

    air_temperature = round(
        22.0
        + 8.0 * daylight
        + random.gauss(0, 1.5),
        2,
    )
    air_temperature = max(15.0, min(35.0, air_temperature))

    air_humidity = round(
        75.0
        - 25.0 * daylight
        + random.gauss(0, 4.0),
        2,
    )
    air_humidity = max(30.0, min(95.0, air_humidity))

    light_percent = round(
        90.0 * daylight
        + random.gauss(0, 8.0),
        2,
    )
    light_percent = max(0.0, min(100.0, light_percent))
    light_raw = int(light_percent / 100.0 * 4095)

    soil_moisture_percent = round(
        60.0
        - 20.0 * daylight
        - 0.4 * air_temperature
        + random.gauss(0, 5.0),
        2,
    )
    soil_moisture_percent = max(0.0, min(100.0, soil_moisture_percent))
    soil_moisture_raw = int((1 - soil_moisture_percent / 100.0) * 4095)

    ph = round(
        6.5
        - 0.02 * air_temperature
        + random.gauss(0, 0.3),
        2,
    )
    ph = max(4.0, min(9.0, ph))

    nitrogen = int(
        180
        - 1.5 * air_temperature
        + 0.5 * soil_moisture_percent
        + random.gauss(0, 15)
    )
    nitrogen = max(0, min(255, nitrogen))

    phosphorus = int(
        160
        - 1.2 * air_temperature
        + 0.4 * soil_moisture_percent
        + random.gauss(0, 15)
    )
    phosphorus = max(0, min(255, phosphorus))

    potassium = int(
        200
        - 1.8 * air_temperature
        + 0.6 * soil_moisture_percent
        + random.gauss(0, 15)
    )
    potassium = max(0, min(255, potassium))

    created_at = base_time + timedelta(minutes=index * 5)

    return {
        "air_humidity": air_humidity,
        "air_temperature": air_temperature,
        "soil_moisture_raw": soil_moisture_raw,
        "soil_moisture_percent": int(soil_moisture_percent),
        "ph": ph,
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "light_raw": light_raw,
        "light_percent": light_percent,
        "latitude": -23.5505,
        "longitude": -46.6333,
        "created_at": created_at,
        "updated_at": created_at,
    }


@app.post("/simulate")
def simulate_soil_data():
    base_time = datetime.now() - timedelta(days=7)
    records = [_generate_correlated_record(i, base_time) for i in range(200)]

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO soil_data (
                        air_humidity,
                        air_temperature,
                        soil_moisture_raw,
                        soil_moisture_percent,
                        ph,
                        nitrogen,
                        phosphorus,
                        potassium,
                        light_raw,
                        light_percent,
                        latitude,
                        longitude,
                        created_at,
                        updated_at
                    ) VALUES (
                        :air_humidity,
                        :air_temperature,
                        :soil_moisture_raw,
                        :soil_moisture_percent,
                        :ph,
                        :nitrogen,
                        :phosphorus,
                        :potassium,
                        :light_raw,
                        :light_percent,
                        :latitude,
                        :longitude,
                        :created_at,
                        :updated_at
                    )
                    """,
                    records,
                )
            connection.commit()
    except oracledb.Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"message": "200 registros simulados inseridos com sucesso"}
