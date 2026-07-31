"""Adaptador de base de datos: sesión y motor de SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    return SessionLocal()
