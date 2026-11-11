import os

import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("ORACLE_USER")
DB_PASSWORD = os.getenv("ORACLE_PASSWORD")
DB_DSN = os.getenv("ORACLE_DSN")

CREATE_TABLE_SQL = """
CREATE TABLE soil_data (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    air_humidity BINARY_FLOAT NOT NULL,
    air_temperature BINARY_FLOAT NOT NULL,
    soil_moisture_raw NUMBER NOT NULL,
    soil_moisture_percent NUMBER NOT NULL,
    ph BINARY_FLOAT NOT NULL,
    nitrogen NUMBER NOT NULL,
    phosphorus NUMBER NOT NULL,
    potassium NUMBER NOT NULL,
    light_raw NUMBER NOT NULL,
    light_percent BINARY_FLOAT NOT NULL,
    latitude BINARY_FLOAT,
    longitude BINARY_FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def create_table():
    with oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN) as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            print("Tabela 'soil_data' criada com sucesso.")
        connection.commit()


if __name__ == "__main__":
    create_table()
