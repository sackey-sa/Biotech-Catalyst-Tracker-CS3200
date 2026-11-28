"""The SQL Showcase. Every query lives in sql/03_queries.sql, one after another, each with:

    -- QUERY N
    -- title: Short name shown on the card
    -- question: The question in plain English
    -- graded: yes | no
    -- (any other comment lines in the header are shown as notes)
    SELECT ...;

    -- Expected with test data:   (optional; never shown or run)

Only queries in that file can be run, so the API never executes SQL sent by the browser.
"""
import re
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.db import BACKEND_DIR, get_db

router = APIRouter(tags=["queries"])
QUERIES_FILE = BACKEND_DIR.parent / "sql" / "03_queries.sql"
REL_PATH = "sql/03_queries.sql"

QUERY_HEADER = re.compile(r"^--\s*QUERY\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
META = re.compile(r"^(title|question|graded)\s*:\s*(.*)$", re.IGNORECASE)
SEPARATOR = re.compile(r"^[-=\s]*$")            # "-- -----" lines and blank "--"
USE_STMT = re.compile(r"^\s*USE\s+\w+\s*;?\s*$", re.IGNORECASE)
EXPECTED = re.compile(r"^--\s*Expected\b", re.IGNORECASE)
STRING_LITERAL = re.compile(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.|\"\")*\"")


def parse_block(number: int, block: str) -> dict:
    meta, notes, paragraph, sql_lines = {}, [], [], []

    def end_paragraph() -> None:
        if paragraph:
            notes.append(" ".join(paragraph))
            paragraph.clear()

    for line in block.splitlines():
        stripped = line.strip()
        if EXPECTED.match(stripped):
            break  # the expected-output comment and anything after it is never shown or run
        if stripped.startswith("--"):
            if sql_lines:
                continue  # comments inside the SQL are dropped
            body = stripped[2:].strip()
            found = META.match(body)
            if found:
                end_paragraph()
                meta[found.group(1).lower()] = found.group(2).strip()
            elif SEPARATOR.match(body):
                end_paragraph()  # a blank "--" or a dashed line ends a note
            else:
                paragraph.append(body)  # wrapped comment lines join into one note
        elif USE_STMT.match(line):
            continue
        elif stripped or sql_lines:
            sql_lines.append(line)
    end_paragraph()
    sql = "\n".join(sql_lines).strip()
    return {
        "slug": f"q{number}",
        "number": number,
        "file": REL_PATH,
        "title": meta.get("title", f"Query {number}"),
        "question": meta.get("question", ""),
        "graded": meta.get("graded", "").lower() == "yes",
        "notes": notes,
        "sql": sql,
    }


def all_queries() -> list[dict]:
    """Graded queries first, then the rest, each in file order."""
    parts = QUERY_HEADER.split(QUERIES_FILE.read_text(encoding="utf-8"))
    # parts = [preamble, "1", block1, "2", block2, ...]; the preamble (file header, USE) is skipped.
    queries = [parse_block(int(n), block) for n, block in zip(parts[1::2], parts[2::2])]
    return sorted(queries, key=lambda q: (not q["graded"], q["number"]))


@router.get("/queries")
def list_queries() -> list[dict]:
    return all_queries()


@router.post("/queries/{slug}/run")
def run_query(slug: str, db: Session = Depends(get_db)) -> dict:
    query = next((q for q in all_queries() if q["slug"] == slug), None)
    if not query:
        raise HTTPException(404, "Query not found")
    sql = query["sql"].rstrip().rstrip(";")
    # A ';' left outside quoted text means a second statement (e.g. SEPARATOR '; ' is fine).
    if not sql or ";" in STRING_LITERAL.sub("''", sql):
        raise HTTPException(400, f"Query {query['number']} must be exactly one SQL statement")
    started = time.perf_counter()
    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        data = [list(r) for r in result]
    except DBAPIError as exc:
        raise HTTPException(400, f"MySQL error in Query {query['number']}: {exc.orig}") from exc
    finally:
        db.rollback()  # showcase queries are SELECTs; never keep anything
    return {"slug": slug, "columns": columns, "rows": jsonable_encoder(data),
            "row_count": len(data), "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}
