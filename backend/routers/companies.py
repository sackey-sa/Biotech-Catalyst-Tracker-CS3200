"""Company list and company profile (pipeline, FDA history, filings, events, prices)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db, one, rows
from backend.routers.events import EVENT_LIST_SQL

router = APIRouter(tags=["companies"])


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)) -> list[dict]:
    return rows(db, """
        SELECT c.company_id, c.name, c.cik, s.ticker,
               (SELECT COUNT(*) FROM trials t WHERE t.company_id = c.company_id)       AS trials,
               (SELECT COUNT(*) FROM fda_actions f WHERE f.company_id = c.company_id)  AS fda_actions,
               (SELECT COUNT(*) FROM events e WHERE e.company_id = c.company_id)       AS events,
               (SELECT AVG(r.abnormal_return_1d) FROM event_returns r
                 WHERE r.company_id = c.company_id)                                     AS avg_abnormal_1d,
               (SELECT p.adjusted_close FROM prices p WHERE p.security_id = s.security_id
                 ORDER BY p.trade_date DESC LIMIT 1)                                    AS last_close
        FROM companies c
        LEFT JOIN securities s ON s.company_id = c.company_id
        ORDER BY c.name""")


@router.get("/companies/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)) -> dict:
    company = one(db, """
        SELECT c.*, s.security_id, s.ticker FROM companies c
        LEFT JOIN securities s ON s.company_id = c.company_id
        WHERE c.company_id = :id""", id=company_id)
    if not company:
        raise HTTPException(404, "Company not found")

    trials = rows(db, """
        SELECT t.*,
               GROUP_CONCAT(DISTINCT co.condition_name ORDER BY co.condition_name SEPARATOR '; ') AS conditions,
               GROUP_CONCAT(DISTINCT COALESCE(d.brand_name, d.active_ingredient) SEPARATOR '; ') AS drugs
        FROM trials t
        LEFT JOIN trial_conditions tc ON tc.nct_number = t.nct_number
        LEFT JOIN conditions co       ON co.condition_id = tc.condition_id
        LEFT JOIN trial_drugs td      ON td.nct_number = t.nct_number
        LEFT JOIN drugs d             ON d.drug_id = td.drug_id
        WHERE t.company_id = :id
        GROUP BY t.nct_number
        ORDER BY t.phase DESC, t.start_date DESC""", id=company_id)

    return {
        "company": company,
        "aliases": rows(db, "SELECT alias_name, source FROM company_aliases WHERE company_id = :id "
                            "ORDER BY source", id=company_id),
        "trials": trials,
        "fda_actions": rows(db, """
            SELECT fa.*, d.brand_name, d.active_ingredient FROM fda_actions fa
            JOIN drugs d ON d.drug_id = fa.drug_id
            WHERE fa.company_id = :id ORDER BY fa.action_date DESC""", id=company_id),
        "filings": rows(db, "SELECT * FROM filings WHERE company_id = :id ORDER BY filing_date DESC",
                        id=company_id),
        "events": rows(db, EVENT_LIST_SQL + " WHERE e.company_id = :id ORDER BY e.event_timestamp",
                       id=company_id),
    }


@router.get("/companies/{company_id}/prices")
def company_prices(company_id: int, date_from: date | None = None, date_to: date | None = None,
                   db: Session = Depends(get_db)) -> list[dict]:
    """Daily closes for the company's stock with XBI alongside, for the profile chart."""
    return rows(db, """
        SELECT p.trade_date, p.adjusted_close AS close, p.volume, x.adjusted_close AS xbi_close
        FROM securities s
        JOIN prices p ON p.security_id = s.security_id
        LEFT JOIN prices x ON x.trade_date = p.trade_date
             AND x.security_id = (SELECT security_id FROM securities WHERE ticker = 'XBI')
        WHERE s.company_id = :id
          AND (:date_from IS NULL OR p.trade_date >= :date_from)
          AND (:date_to IS NULL OR p.trade_date <= :date_to)
        ORDER BY p.trade_date""", id=company_id, date_from=date_from, date_to=date_to)
