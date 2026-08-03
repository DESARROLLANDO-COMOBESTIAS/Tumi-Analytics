"""Catálogo de ciudades desde la fuente de verdad (PostgreSQL)."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tumi_shared.models import City

from etl.config import DATABASE_URL


def get_cities() -> list[City]:
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        return list(session.scalars(select(City).order_by(City.name)))
