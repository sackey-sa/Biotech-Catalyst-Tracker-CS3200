"""filings: 8-Ks from SEC EDGAR for every company with a CIK."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Companies, Filings
from pipeline.db_utils import upsert
from pipeline.sources import sec_edgar

log = logging.getLogger(__name__)


def load(session: Session) -> None:
    for company in session.scalars(select(Companies)).all():
        rows = [{"accession_number": f["accession_number"], "company_id": company.company_id,
                 "form_type": f["form_type"], "filing_date": f["filing_date"],
                 "acceptance_timestamp": f["acceptance_timestamp"]}
                for f in sec_edgar.filings(company.cik)]
        upsert(session, Filings, rows, ["accession_number"])
        session.commit()
        log.info("%s: %d filings", company.name, len(rows))
