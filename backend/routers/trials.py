"""Clinical trials explorer with filter options."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db, rows

router = APIRouter(tags=["trials"])


@router.get("/trials")
def list_trials(phase: str | None = None, status: str | None = None, condition_id: int | None = None,
                company_id: int | None = None, q: str | None = None,
                db: Session = Depends(get_db)) -> list[dict]:
    where, params = [], {}
    if phase:
        where.append("t.phase = :phase"); params["phase"] = phase
    if status:
        where.append("t.status = :status"); params["status"] = status
    if company_id:
        where.append("t.company_id = :company_id"); params["company_id"] = company_id
    if condition_id:
        where.append("EXISTS (SELECT 1 FROM trial_conditions x WHERE x.nct_number = t.nct_number "
                     "AND x.condition_id = :condition_id)")
        params["condition_id"] = condition_id
    if q:
        # EXISTS only decides which trials match; the conditions and drugs columns
        # below still list every condition and drug of a matching trial.
        where.append("""(t.nct_number LIKE :q OR c.name LIKE :q
            OR EXISTS (SELECT 1 FROM trial_conditions xc
                       JOIN conditions xco ON xco.condition_id = xc.condition_id
                       WHERE xc.nct_number = t.nct_number AND xco.condition_name LIKE :q)
            OR EXISTS (SELECT 1 FROM trial_drugs xd
                       JOIN drugs xdr ON xdr.drug_id = xd.drug_id
                       WHERE xd.nct_number = t.nct_number
                         AND (xdr.active_ingredient LIKE :q OR xdr.brand_name LIKE :q)))""")
        params["q"] = f"%{q}%"
    return rows(db, f"""
        SELECT t.nct_number, t.phase, t.status, t.enrollment, t.start_date, t.completion_date,
               c.company_id, c.name AS company_name, s.ticker,
               GROUP_CONCAT(DISTINCT co.condition_name ORDER BY co.condition_name SEPARATOR '; ') AS conditions,
               GROUP_CONCAT(DISTINCT COALESCE(d.brand_name, d.active_ingredient) SEPARATOR '; ') AS drugs,
               MAX(e.event_id) AS readout_event_id,
               MAX(e.outcome)  AS readout_outcome
        FROM trials t
        JOIN companies c              ON c.company_id = t.company_id
        LEFT JOIN securities s        ON s.company_id = c.company_id
        LEFT JOIN trial_conditions tc ON tc.nct_number = t.nct_number
        LEFT JOIN conditions co       ON co.condition_id = tc.condition_id
        LEFT JOIN trial_drugs td      ON td.nct_number = t.nct_number
        LEFT JOIN drugs d             ON d.drug_id = td.drug_id
        LEFT JOIN events e            ON e.nct_number = t.nct_number
        {"WHERE " + " AND ".join(where) if where else ""}
        GROUP BY t.nct_number, c.company_id, s.ticker
        ORDER BY t.start_date DESC""", **params)


@router.get("/trials/facets")
def trial_facets(db: Session = Depends(get_db)) -> dict:
    """Values for the filter dropdowns, with how many trials each has."""
    return {
        "phases": rows(db, "SELECT phase AS value, COUNT(*) AS n FROM trials "
                           "WHERE phase IS NOT NULL GROUP BY phase ORDER BY phase"),
        "statuses": rows(db, "SELECT status AS value, COUNT(*) AS n FROM trials GROUP BY status ORDER BY n DESC"),
        "conditions": rows(db, """
            SELECT co.condition_id AS value, co.condition_name AS label, COUNT(*) AS n
            FROM conditions co JOIN trial_conditions tc ON tc.condition_id = co.condition_id
            GROUP BY co.condition_id ORDER BY co.condition_name"""),
        "by_phase_status": rows(db, "SELECT phase, status, COUNT(*) AS n FROM trials GROUP BY phase, status"),
    }
