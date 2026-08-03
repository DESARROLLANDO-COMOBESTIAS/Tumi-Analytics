"""Modelos SQLAlchemy del star schema (reesportados desde el paquete compartido).

La fuente única de verdad vive en `shared.models`; este módulo preserva los
imports existentes del backend.
"""

from tumi_shared.models import (  # noqa: F401
    Base,
    CalendarDay,
    City,
    DailyCityFact,
    PoiCategory,
    TourismScoreFact,
)
