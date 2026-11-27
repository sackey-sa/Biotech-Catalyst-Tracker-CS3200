"""fda_actions (+ drugs): original FDA applications from openFDA."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import FdaActions
from pipeline.loaders.common import (AliasRegistry, DrugRegistry, company_ids_by_ticker,
                                     read_seed_companies)
from pipeline.normalize import name_key
from pipeline.sources import openfda

log = logging.getLogger(__name__)


def load(session: Session) -> None:
    ids = company_ids_by_ticker(session)
    aliases, drugs = AliasRegistry(session), DrugRegistry(session)
    existing = {a.application_number: a for a in session.scalars(select(FdaActions))}

    for seed in read_seed_companies():
        company_id = ids.get(seed.ticker)
        if company_id is None:
            continue
        count = 0
        for prefix in seed.openfda_prefixes:
            for app in openfda.applications_by_sponsor_prefix(prefix):
                # The wildcard is a raw string prefix ("BIOGEN*" would also hit "BIOGENERICS"),
                # so require the sponsor's leading word(s) to equal the prefix.
                sponsor_words = name_key(app["sponsor_name"] or "").split()
                prefix_words = name_key(prefix).split()
                if sponsor_words[:len(prefix_words)] != prefix_words:
                    continue
                aliases.add(app["sponsor_name"], company_id, "openfda")

                values = {
                    "company_id": company_id,
                    "drug_id": drugs.for_fda(app["brand_name"], app["active_ingredient"]),
                    "submission_type": app["submission_type"],
                    "status": app["status"],
                    "action_date": app["action_date"],
                }
                row = existing.get(app["application_number"])
                if row is None:
                    row = FdaActions(application_number=app["application_number"], **values)
                    session.add(row)
                    existing[row.application_number] = row
                elif row.company_id != company_id:
                    log.warning("%s already belongs to company %s; skipping",
                                row.application_number, row.company_id)
                    continue
                else:
                    for k, v in values.items():
                        setattr(row, k, v)
                count += 1
        session.commit()
        log.info("%s: %d FDA applications", seed.ticker, count)
