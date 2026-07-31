"""Configuración de conexión a PostgreSQL."""

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://tumi:tumi_dev@localhost:5433/tumi",
)
