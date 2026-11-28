"""The graded showcase queries. Each lives in backend/queries/NN_slug.sql with a header:

    -- title: Short name shown on the card
    -- question: The question in plain English
    -- (any other comment lines are shown as notes)
    SELECT ...;

Only files in that folder can be run, so the API never executes SQL sent by the browser.
"""
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import BACKEND_DIR, get_db

router = APIRouter(tags=["queries"])
QUERY_DIR = BACKEND_DIR / "queries"


def parse(path: Path) -> dict:
    meta, notes, sql_lines = {}, [], []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("--") and not sql_lines:
            body = stripped[2:].strip()
            key, sep, value = body.partition(":")
            if sep and key.lower() in ("title", "question"):
                meta[key.lower()] = value.strip()
            elif body:
                notes.append(body)
        else:
            sql_lines.append(line)
    slug = path.stem.split("_", 1)[-1]
    return {"slug": slug, "file": path.name, "title": meta.get("title", slug),
            "question": meta.get("question", ""), "notes": notes,
            "sql": "\n".join(sql_lines).strip()}


def all_queries() -> list[dict]:
    return [parse(p) for p in sorted(QUERY_DIR.glob("*.sql"))]


@router.get("/queries")
def list_queries() -> list[dict]:
    return all_queries()


@router.post("/queries/{slug}/run")
def run_query(slug: str, db: Session = Depends(get_db)) -> dict:
    query = next((q for q in all_queries() if q["slug"] == slug), None)
    if not query:
        raise HTTPException(404, "Query not found")
    started = time.perf_counter()
    result = db.execute(text(query["sql"].rstrip(";")))
    columns = list(result.keys())
    data = [list(r) for r in result]
    db.rollback()  # showcase queries are SELECTs; never keep anything
    return {"slug": slug, "columns": columns, "rows": jsonable_encoder(data),
            "row_count": len(data), "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}
