"""Event list with filters, and a single event with its price reaction."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db import get_db, one, rows

router = APIRouter(tags=["events"])

# Shared by the list, the dashboard and company pages.
EVENT_LIST_SQL = """
    SELECT e.event_id, e.event_type, e.outcome, e.event_timestamp, e.trading_day,
           e.nct_number, e.fda_action_id, e.accession_number, e.source_url,
           c.company_id, c.name AS company_name, c.cik, s.ticker,
           t.phase,
           COALESCE(d.brand_name, d.active_ingredient) AS fda_drug,
           r.stock_return    AS stock_return_1d,
           r.xbi_return      AS xbi_return_1d,
           r.abnormal_return AS abnormal_return_1d,
           w.stock_return_5d, w.abnormal_return_5d
    FROM events e
    JOIN companies c          ON c.company_id = e.company_id
    LEFT JOIN securities s    ON s.company_id = c.company_id
    LEFT JOIN trials t        ON t.nct_number = e.nct_number
    LEFT JOIN fda_actions fa  ON fa.fda_action_id = e.fda_action_id
    LEFT JOIN drugs d         ON d.drug_id = fa.drug_id
    LEFT JOIN event_returns r ON r.event_id = e.event_id   -- team view (sql/02_calculations.sql)
    LEFT JOIN event_windows w ON w.event_id = e.event_id   -- backend view (backend/sql/views.sql)
"""

SORTS = {"date": "e.event_timestamp", "abnormal_1d": "r.abnormal_return",
         "abnormal_5d": "w.abnormal_return_5d", "company": "c.name"}


@router.get("/events")
def list_events(
    event_type: str | None = Query(None, description="fda_decision or trial_readout"),
    outcome: str | None = None,
    company_id: int | None = None,
    q: str | None = Query(None, description="search company name or ticker"),
    date_from: date | None = None,
    date_to: date | None = None,
    sort: Literal["date", "abnormal_1d", "abnormal_5d", "company"] = "date",
    order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> list[dict]:
    where, params = [], {}
    if event_type:
        where.append("e.event_type = :event_type"); params["event_type"] = event_type
    if outcome:
        where.append("e.outcome = :outcome"); params["outcome"] = outcome
    if company_id:
        where.append("e.company_id = :company_id"); params["company_id"] = company_id
    if q:
        where.append("(c.name LIKE :q OR s.ticker LIKE :q)"); params["q"] = f"%{q}%"
    if date_from:
        where.append("e.trading_day >= :date_from"); params["date_from"] = date_from
    if date_to:
        where.append("e.trading_day <= :date_to"); params["date_to"] = date_to
    sql = EVENT_LIST_SQL + (" WHERE " + " AND ".join(where) if where else "")
    # sort/order come from fixed lists above, so formatting them in is safe.
    sql += f" ORDER BY {SORTS[sort]} IS NULL, {SORTS[sort]} {order.upper()}"
    return rows(db, sql, **params)


@router.get("/events/{event_id}")
def get_event(event_id: int, window: int = Query(10, ge=3, le=30), db: Session = Depends(get_db)) -> dict:
    event = one(db, EVENT_LIST_SQL + " WHERE e.event_id = :id", id=event_id)
    if not event:
        raise HTTPException(404, "Event not found")

    trial = None
    if event["nct_number"]:
        trial = one(db, "SELECT * FROM trials WHERE nct_number = :n", n=event["nct_number"])
        trial["conditions"] = rows(db, """
            SELECT co.condition_id, co.condition_name FROM trial_conditions tc
            JOIN conditions co ON co.condition_id = tc.condition_id
            WHERE tc.nct_number = :n""", n=event["nct_number"])
        trial["drugs"] = rows(db, """
            SELECT d.* FROM trial_drugs td JOIN drugs d ON d.drug_id = td.drug_id
            WHERE td.nct_number = :n""", n=event["nct_number"])

    fda_action = None
    if event["fda_action_id"]:
        fda_action = one(db, """
            SELECT fa.*, d.brand_name, d.active_ingredient FROM fda_actions fa
            JOIN drugs d ON d.drug_id = fa.drug_id WHERE fa.fda_action_id = :id""",
                         id=event["fda_action_id"])

    filing = None
    if event["accession_number"]:
        filing = one(db, "SELECT * FROM filings WHERE accession_number = :a", a=event["accession_number"])

    return {"event": event, "trial": trial, "fda_action": fda_action, "filing": filing,
            "price_window": price_window(db, event_id, window)}


def price_window(db: Session, event_id: int, window: int) -> list[dict]:
    """Stock and XBI around the event, both indexed to 100 at the close before the event (day -1).
    day 0 is the event's trading day."""
    return rows(db, """
        WITH ev AS (
            SELECT e.trading_day, s.security_id AS stock_id,
                   (SELECT security_id FROM securities WHERE ticker = 'XBI') AS xbi_id
            FROM events e JOIN securities s ON s.company_id = e.company_id
            WHERE e.event_id = :event_id
        ),
        anchor AS (
            SELECT pi.day_idx FROM price_index pi JOIN ev
              ON pi.security_id = ev.stock_id AND pi.trade_date = ev.trading_day
        ),
        stock AS (
            SELECT pi.trade_date, pi.day_idx - anchor.day_idx AS rel_day, pi.adjusted_close
            FROM price_index pi JOIN ev JOIN anchor
            WHERE pi.security_id = ev.stock_id
              AND pi.day_idx BETWEEN anchor.day_idx - :w AND anchor.day_idx + :w
        ),
        xbi AS (
            SELECT p.trade_date, p.adjusted_close FROM prices p JOIN ev ON p.security_id = ev.xbi_id
        ),
        base AS (
            SELECT stock.adjusted_close AS stock0, xbi.adjusted_close AS xbi0
            FROM stock LEFT JOIN xbi ON xbi.trade_date = stock.trade_date
            WHERE stock.rel_day = -1
        )
        SELECT stock.rel_day, stock.trade_date,
               stock.adjusted_close              AS stock_close,
               xbi.adjusted_close                AS xbi_close,
               100 * stock.adjusted_close / base.stock0 AS stock_indexed,
               100 * xbi.adjusted_close / base.xbi0     AS xbi_indexed
        FROM stock
        LEFT JOIN xbi ON xbi.trade_date = stock.trade_date
        CROSS JOIN base
        ORDER BY stock.rel_day""", event_id=event_id, w=window)
