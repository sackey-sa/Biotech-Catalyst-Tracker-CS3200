"""Shared database helpers for the API. Reuses the engine from the repo's database.py."""
from collections.abc import Iterator
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SESSION_LOCAL, engine

# database.py turns on SQL echo for debugging; it floods the API log, so quiet it here.
engine.echo = False

BACKEND_DIR = Path(__file__).resolve().parent


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SESSION_LOCAL()
    try:
        yield db
    finally:
        db.close()


def rows(db: Session, sql: str, **params) -> list[dict]:
    """Run raw SQL and return JSON-safe dicts (Decimal -> float, date -> ISO string)."""
    result = db.execute(text(sql), params)
    return jsonable_encoder([dict(r._mapping) for r in result])


def one(db: Session, sql: str, **params) -> dict | None:
    found = rows(db, sql, **params)
    return found[0] if found else None
