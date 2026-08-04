"""Carga en PostgreSQL (fuente de verdad) con upserts idempotentes."""

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from tumi_shared.models import (
    CalendarDay,
    City,
    DailyCityFact,
    PoiCategory,
    PoiCityFact,
)

from etl.config import DATABASE_URL

SEASON_BY_MONTH = {
    1: "verano",
    2: "verano",
    3: "otono",
    4: "otono",
    5: "otono",
    6: "invierno",
    7: "invierno",
    8: "invierno",
    9: "primavera",
    10: "primavera",
    11: "primavera",
    12: "verano",
}

WEATHER_COLUMNS = ("temperature_c", "humidity", "precipitation_mm", "wind_speed_kmh")


def _season(month: int) -> str:
    return SEASON_BY_MONTH[month]


def _upsert_calendar_day(session: Session, day: date) -> None:
    statement = (
        insert(CalendarDay)
        .values(date=day, year=day.year, month=day.month, day=day.day, season=_season(day.month))
        .on_conflict_do_nothing(index_elements=["date"])
    )
    session.execute(statement)


def load_weather(sync_date: date, records: list[dict]) -> int:
    """Inserta/actualiza clima diario por ciudad. Devuelve nº de ciudades cargadas."""
    engine = create_engine(DATABASE_URL)
    loaded = 0
    with Session(engine) as session:
        _upsert_calendar_day(session, sync_date)
        cities = {c.name: c for c in session.scalars(select(City))}
        for record in records:
            city = cities.get(record["city"])
            if city is None:
                continue
            values = {col: record[col] for col in WEATHER_COLUMNS}
            _upsert_daily_fact(session, city.id, sync_date, values)
            loaded += 1
        session.commit()
    return loaded


def load_exchange_rate(sync_date: date, rate: float) -> int:
    """Escribe el tipo de cambio USD→PEN del día para todas las ciudades."""
    engine = create_engine(DATABASE_URL)
    loaded = 0
    with Session(engine) as session:
        _upsert_calendar_day(session, sync_date)
        city_ids = list(session.scalars(select(City.id)))
        for city_id in city_ids:
            _upsert_daily_fact(session, city_id, sync_date, {"exchange_rate": rate})
            loaded += 1
        session.commit()
    return loaded


def _upsert_daily_fact(session: Session, city_id: int, day: date, values: dict) -> None:
    statement = insert(DailyCityFact).values(city_id=city_id, date_id=day, **values)
    statement = statement.on_conflict_do_update(
        index_elements=["city_id", "date_id"],
        set_={column: statement.excluded[column] for column in values},
    )
    session.execute(statement)


def load_poi(sync_date: date, per_city: dict[str, dict[str, int]]) -> int:
    """Escribe conteos de POIs por ciudad/categoría en fact_poi_city.

    ``per_city`` mapea nombre de ciudad -> {código_categoría: conteo}.
    Devuelve el nº de filas insertadas/actualizadas (solo conteos > 0).
    """
    engine = create_engine(DATABASE_URL)
    loaded = 0
    with Session(engine) as session:
        _upsert_calendar_day(session, sync_date)
        cities = {c.name: c for c in session.scalars(select(City))}
        categories = {c.code: c for c in session.scalars(select(PoiCategory))}
        for city_name, counts in per_city.items():
            city = cities.get(city_name)
            if city is None:
                continue
            for code, count in counts.items():
                if count <= 0:
                    continue
                category = categories.get(code)
                if category is None:
                    continue
                statement = insert(PoiCityFact).values(
                    city_id=city.id, date_id=sync_date,
                    poi_category_id=category.id, count=count,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=["city_id", "date_id", "poi_category_id"],
                    set_={"count": statement.excluded["count"]},
                )
                session.execute(statement)
                loaded += 1
        session.commit()
    return loaded
