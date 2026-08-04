"""Configuración del pipeline ETL vía variables de entorno."""

import os

AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://tumi:tumi_dev@localhost:5433/tumi",
)
BRONZE_BUCKET = os.getenv("BRONZE_BUCKET", "tumi-bronze")
SILVER_BUCKET = os.getenv("SILVER_BUCKET", "tumi-silver")

SOURCE_OPEN_METEO = "open_meteo"
SOURCE_EXCHANGE_RATE = "exchange_rate"
SOURCE_POI = "poi"
