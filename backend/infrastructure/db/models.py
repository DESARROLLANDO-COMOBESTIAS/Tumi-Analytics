"""Modelos SQLAlchemy del star schema de Tumi Analytics (capa de infraestructura)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "dim_city"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    department: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    population: Mapped[int] = mapped_column(Integer)

    daily_metrics: Mapped[list["DailyCityFact"]] = relationship(
        back_populates="city"
    )
    scores: Mapped[list["TourismScoreFact"]] = relationship(back_populates="city")


class CalendarDay(Base):
    __tablename__ = "dim_date"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    season: Mapped[str] = mapped_column(String(20))

    daily_metrics: Mapped[list["DailyCityFact"]] = relationship(
        back_populates="calendar_day"
    )
    scores: Mapped[list["TourismScoreFact"]] = relationship(
        back_populates="calendar_day"
    )


class PoiCategory(Base):
    __tablename__ = "dim_poi_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class DailyCityFact(Base):
    __tablename__ = "fact_daily_city"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("dim_city.id"))
    date_id: Mapped[date] = mapped_column(ForeignKey("dim_date.date"))
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    hotels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    restaurants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    museums: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hospitals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exchange_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    city: Mapped[City] = relationship(back_populates="daily_metrics")
    calendar_day: Mapped[CalendarDay] = relationship(
        back_populates="daily_metrics"
    )


class TourismScoreFact(Base):
    __tablename__ = "fact_tourism_score"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("dim_city.id"))
    date_id: Mapped[date] = mapped_column(ForeignKey("dim_date.date"))
    score: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    city: Mapped[City] = relationship(back_populates="scores")
    calendar_day: Mapped[CalendarDay] = relationship(back_populates="scores")
