"""trials, conditions, trial_conditions, trial_drugs (+ drugs) from ClinicalTrials.gov."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Conditions, TrialConditions, TrialDrugs, Trials
from pipeline.db_utils import upsert
from pipeline.loaders.common import (AliasRegistry, DrugRegistry, company_ids_by_ticker,
                                     read_seed_companies)
from pipeline.normalize import clean_intervention_name, clip, fold, name_key
from pipeline.sources import clinicaltrials

log = logging.getLogger(__name__)


def _sponsor_matches(lead_sponsor: str | None, term: str) -> bool:
    """query.lead is a fuzzy search; keep only sponsors whose name starts with the search term."""
    if not lead_sponsor:
        return False
    key, want = name_key(lead_sponsor), name_key(term)
    return key == want or key.startswith(want + " ")


class _ConditionRegistry:
    def __init__(self, session: Session):
        self.session = session
        self.ids = {fold(c.condition_name): c.condition_id for c in session.scalars(select(Conditions))}

    def id_for(self, name: str) -> int | None:
        name = clip(name, 255)
        if not name:
            return None
        if fold(name) not in self.ids:
            c = Conditions(condition_name=name)
            self.session.add(c)
            self.session.flush()
            self.ids[fold(name)] = c.condition_id
        return self.ids[fold(name)]


def load(session: Session) -> None:
    ids = company_ids_by_ticker(session)
    aliases, drugs, conditions = AliasRegistry(session), DrugRegistry(session), _ConditionRegistry(session)
    owner = dict(session.execute(select(Trials.nct_number, Trials.company_id)).all())

    for seed in read_seed_companies():
        company_id = ids.get(seed.ticker)
        if company_id is None:
            continue
        trials, cond_links, drug_links = {}, set(), set()
        for term in seed.ctgov_sponsors:
            for t in clinicaltrials.trials_by_lead_sponsor(term):
                if not (_sponsor_matches(t["lead_sponsor"], term)
                        or aliases.company_for(t["lead_sponsor"]) == company_id):
                    continue
                nct = t["nct_number"]
                if owner.get(nct, company_id) != company_id:
                    continue  # already loaded under another company
                aliases.add(t["lead_sponsor"], company_id, "clinicaltrials")
                trials[nct] = {
                    "nct_number": nct, "company_id": company_id,
                    "phase": clip(t["phase"], 50), "status": clip(t["status"], 40),
                    "enrollment": t["enrollment"],
                    "start_date": t["start_date"], "completion_date": t["completion_date"],
                }
                for c in t["conditions"]:
                    if (cid := conditions.id_for(c)) is not None:
                        cond_links.add((nct, cid))
                for name in t["drugs"]:
                    cleaned = clean_intervention_name(name)
                    if cleaned and (did := drugs.for_trial(cleaned)) is not None:
                        drug_links.add((nct, did))

        upsert(session, Trials, list(trials.values()), ["nct_number"])
        upsert(session, TrialConditions, [{"nct_number": n, "condition_id": c} for n, c in cond_links],
               ["nct_number", "condition_id"])
        upsert(session, TrialDrugs, [{"nct_number": n, "drug_id": d} for n, d in drug_links],
               ["nct_number", "drug_id"])
        session.commit()
        owner.update({n: company_id for n in trials})
        log.info("%s: %d trials, %d condition links, %d drug links",
                 seed.ticker, len(trials), len(cond_links), len(drug_links))

