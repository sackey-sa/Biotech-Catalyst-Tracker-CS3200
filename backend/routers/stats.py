"""Dashboard numbers: table counts, average reaction by outcome, latest events."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db, one, rows
from backend.routers.events import EVENT_LIST_SQL

router = APIRouter(tags=["stats"])

TABLES = ["companies", "securities", "prices", "drugs", "conditions", "trials",
          "fda_actions", "filings", "events"]


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)) -> dict:
    counts = one(db, "SELECT " + ", ".join(f"(SELECT COUNT(*) FROM {t}) AS {t}" for t in TABLES))
    demo = one(db, "SELECT COUNT(*) AS n FROM companies WHERE cik LIKE '999999%'")["n"] > 0
    by_outcome = rows(db, """
        SELECT e.event_type, e.outcome,
               COUNT(*)                  AS events,
               AVG(r.abnormal_return)    AS avg_abnormal_1d,
               AVG(w.abnormal_return_5d) AS avg_abnormal_5d
        FROM events e
        LEFT JOIN event_returns r ON r.event_id = e.event_id
        LEFT JOIN event_windows w ON w.event_id = e.event_id
        GROUP BY e.event_type, e.outcome
        ORDER BY e.event_type, avg_abnormal_1d DESC""")
    recent = rows(db, EVENT_LIST_SQL + " ORDER BY e.event_timestamp DESC LIMIT 6")
    price_range = one(db, "SELECT MIN(trade_date) AS first, MAX(trade_date) AS last FROM prices")
    return {"counts": counts, "demo_data": demo, "by_outcome": by_outcome,
            "recent_events": recent, "price_range": price_range}
