"""Fill the database with FICTIONAL demo data so the frontend has something to show
before the real loaders (EDGAR, ClinicalTrials.gov, openFDA, prices) exist.

Every company, drug, trial, filing and price here is made up:
  * company CIKs start with 999999  (the API uses this to show a "Demo data" badge)
  * NCT numbers start with NCT99, application numbers with NDA 999 / BLA 999
  * prices are a random walk (fixed seed, so every run gives the same data)

Run from the repo root:
  python -m backend.seed_demo            # seed an empty database
  python -m backend.seed_demo --reset    # wipe demo data and seed again
  python -m backend.seed_demo --clear    # wipe demo data only
"""
import argparse
import random
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select, text

from backend.db import SESSION_LOCAL
from models import (Companies, CompanyAliases, Conditions, Drugs, Events, FdaActions,
                    Filings, Prices, Securities, TrialConditions, TrialDrugs, Trials)

DEMO_CIK_PREFIX = "999999"
START, END = date(2024, 1, 2), date(2025, 12, 31)

# Delete children before parents so foreign keys never block us.
DELETE_ORDER = [Events, TrialDrugs, TrialConditions, FdaActions, Filings, Trials, Prices,
                Securities, CompanyAliases, Drugs, Conditions, Companies]

COMPANIES = [
    # name, ticker, drug-code prefix, ingredient stem, focus conditions
    ("Halcyon Biosciences", "HLCN", "HLC", "halci", ["Non-small cell lung cancer", "Glioblastoma"]),
    ("Meridian Oncology", "MRDO", "MRD", "meridi", ["Non-small cell lung cancer", "Pancreatic cancer"]),
    ("Verdant Gene Therapeutics", "VGNT", "VGT", "verda", ["Duchenne muscular dystrophy", "Hemophilia A"]),
    ("Corvane Pharma", "CRVN", "CRV", "corva", ["Type 2 diabetes", "Obesity"]),
    ("Tessellate Bio", "TSLB", "TSL", "tessa", ["Rheumatoid arthritis", "Psoriasis"]),
    ("Northwind Neurosciences", "NWNS", "NWN", "northa", ["Alzheimer's disease", "Major depressive disorder"]),
    ("Aquila Immunotherapeutics", "AQLI", "AQL", "aquili", ["Psoriasis", "Glioblastoma"]),
    ("Pellucid Rare Disease", "PLRD", "PLR", "pellu", ["Sickle cell disease", "Cystic fibrosis"]),
]
SUFFIXES = ["mab", "nib", "tide", "gene", "stat", "cel"]
BRANDS = ["Aurelza", "Brivana", "Cendora", "Dalvexa", "Elymra", "Fortiva", "Glimora", "Hexalyn",
          "Isolva", "Jovira", "Kestra", "Lumevo", "Mirabel", "Novexa", "Orvanta", "Praxela"]

# Mean / spread of the one-day jump for each outcome (fraction, e.g. 0.18 = +18%).
JUMPS = {"approved": (0.07, 0.06), "rejected": (-0.30, 0.10),
         "positive": (0.18, 0.12), "negative": (-0.38, 0.15), "mixed": (-0.04, 0.08)}
PHASE_SCALE = {"PHASE1": 0.5, "PHASE1/PHASE2": 0.7, "PHASE2": 1.0, "PHASE3": 1.3}


def trading_days() -> list[date]:
    days, d = [], START
    while d <= END:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def clear(db, force: bool) -> None:
    real = db.scalar(select(func.count()).select_from(Companies)
                     .where(~Companies.cik.startswith(DEMO_CIK_PREFIX)))
    if real and not force:
        sys.exit(f"Refusing to clear: {real} non-demo companies exist. Pass --force to wipe everything.")
    for model in DELETE_ORDER:
        db.execute(delete(model))
    db.commit()
    # DELETE keeps AUTO_INCREMENT counters; restart them so a fresh seed gets ids 1, 2, 3...
    for table in ("companies", "company_aliases", "securities", "drugs", "conditions",
                  "fda_actions", "events"):
        db.execute(text(f"ALTER TABLE {table} AUTO_INCREMENT = 1"))
    print("Cleared all rows.")


def seed(db) -> None:
    if db.scalar(select(func.count()).select_from(Companies)):
        sys.exit("Database already has companies. Use --reset to replace demo data.")

    rng = random.Random(3200)
    days = trading_days()
    day_pos = {d: i for i, d in enumerate(days)}
    brands = iter(BRANDS)

    conditions = {}
    for _, _, _, _, conds in COMPANIES:
        for c in conds:
            if c not in conditions:
                conditions[c] = Conditions(condition_name=c)
    db.add_all(conditions.values())

    xbi = Securities(ticker="XBI", company_id=None, type="etf")
    db.add(xbi)

    # events_by_security: security -> {trading_day: jump}
    jumps: dict[str, dict[date, float]] = {}
    securities = {"XBI": xbi}
    nct_seq, app_seq, acc_seq = 100001, 900101, 1

    for idx, (name, ticker, code, stem, conds) in enumerate(COMPANIES, start=1):
        cik = f"{DEMO_CIK_PREFIX}{idx:04d}"
        company = Companies(name=name, cik=cik)
        db.add(company)
        db.flush()
        db.add_all([
            CompanyAliases(alias_name=f"{name.upper()} INC", company_id=company.company_id, source="sec"),
            CompanyAliases(alias_name=f"{name}, Inc.", company_id=company.company_id, source="clinicaltrials"),
        ])
        sec = Securities(ticker=ticker, company_id=company.company_id, type="stock")
        db.add(sec)
        securities[ticker] = sec
        jumps[ticker] = {}
        used_days: set[date] = set()

        def pick_event_moment() -> tuple[datetime, date]:
            """Random news moment; pre-market news trades same day, after-close news trades next day."""
            while True:
                i = rng.randrange(40, len(days) - 15)
                d = days[i]
                after_close = rng.random() < 0.4
                trade_day = days[i + 1] if after_close else d
                if trade_day not in used_days:
                    used_days.add(trade_day)
                    ts = datetime.combine(d, time(21, 5) if after_close else time(11, 30))
                    return ts + timedelta(minutes=rng.randrange(0, 50)), trade_day

        def add_filing(ts: datetime | None, form: str = "8-K") -> str:
            nonlocal acc_seq
            acc = f"{cik}-{(ts.year if ts else 2025) % 100:02d}-{acc_seq:06d}"
            acc_seq += 1
            accepted = ts + timedelta(hours=rng.uniform(0.2, 26)) if ts else None
            filed = accepted.date() if accepted else days[rng.randrange(len(days))]
            db.add(Filings(accession_number=acc, company_id=company.company_id, form_type=form,
                           filing_date=filed, acceptance_timestamp=accepted))
            # models.py has no relationship() links, so SQLAlchemy can't order inserts by FK.
            # Flush now so the filing exists before any event that points at it.
            db.flush()
            return acc

        # A few routine filings with no event attached.
        for q in range(rng.randint(2, 4)):
            add_filing(None, rng.choice(["10-Q", "10-K", "8-K"]))

        for n in range(rng.randint(2, 3)):
            suffix = rng.choice(SUFFIXES)
            drug = Drugs(brand_name=None, active_ingredient=f"{stem}{suffix}")
            db.add(drug)
            db.flush()
            phases = rng.sample(["PHASE1", "PHASE1/PHASE2", "PHASE2", "PHASE3"], k=rng.randint(1, 2))
            for phase in sorted(phases):
                cond = rng.choice(conds)
                status = rng.choices(["COMPLETED", "ACTIVE_NOT_RECRUITING", "RECRUITING", "TERMINATED"],
                                     weights=[5, 2, 2, 1])[0]
                start = days[rng.randrange(0, 200)] - timedelta(days=rng.randrange(200, 900))
                trial = Trials(nct_number=f"NCT99{nct_seq:06d}", company_id=company.company_id,
                               phase=phase, status=status,
                               enrollment=rng.choice([24, 48, 80, 120, 240, 450, 800]),
                               start_date=start,
                               completion_date=start + timedelta(days=rng.randrange(400, 1400)))
                nct_seq += 1
                db.add(trial)
                db.flush()
                db.add(TrialConditions(nct_number=trial.nct_number,
                                       condition_id=conditions[cond].condition_id))
                db.add(TrialDrugs(nct_number=trial.nct_number, drug_id=drug.drug_id))

                if status in ("COMPLETED", "TERMINATED", "ACTIVE_NOT_RECRUITING") and rng.random() < 0.85:
                    outcome = ("negative" if status == "TERMINATED" else
                               rng.choices(["positive", "negative", "mixed"], weights=[45, 30, 25])[0])
                    ts, tday = pick_event_moment()
                    mu, sd = JUMPS[outcome]
                    jumps[ticker][tday] = max(-0.85, rng.gauss(mu, sd) * PHASE_SCALE[phase])
                    acc = add_filing(ts)
                    db.add(Events(company_id=company.company_id, event_type="trial_readout",
                                  outcome=outcome, event_timestamp=ts, trading_day=tday,
                                  nct_number=trial.nct_number, accession_number=acc))

            # Late-stage drugs sometimes reach an FDA decision.
            if "PHASE3" in phases and rng.random() < 0.75:
                outcome = rng.choices(["approved", "rejected"], weights=[70, 30])[0]
                ts, tday = pick_event_moment()
                kind = rng.choice(["NDA", "BLA"])
                action = FdaActions(application_number=f"{kind} {app_seq}", company_id=company.company_id,
                                    drug_id=drug.drug_id, submission_type="ORIG",
                                    status="AP" if outcome == "approved" else "CRL",
                                    action_date=ts.date())
                app_seq += 1
                if outcome == "approved":
                    drug.brand_name = next(brands)
                db.add(action)
                db.flush()
                mu, sd = JUMPS[outcome]
                jumps[ticker][tday] = max(-0.85, rng.gauss(mu, sd))
                acc = add_filing(ts) if rng.random() < 0.6 else None
                db.add(Events(company_id=company.company_id, event_type="fda_decision",
                              outcome=outcome, event_timestamp=ts, trading_day=tday,
                              fda_action_id=action.fda_action_id, accession_number=acc))
    db.flush()

    # Prices: XBI random walk; each stock = beta * XBI + its own noise + event jumps.
    xbi_returns = [rng.gauss(0.0003, 0.015) for _ in days]
    price_rows = []
    for ticker, sec in securities.items():
        price = rng.uniform(70, 95) if ticker == "XBI" else rng.uniform(8, 80)
        beta = 1.0 if ticker == "XBI" else rng.uniform(0.9, 1.6)
        base_volume = 9_000_000 if ticker == "XBI" else rng.randrange(300_000, 3_000_000)
        drift_left, drift = 0, 0.0
        for i, d in enumerate(days):
            if ticker == "XBI":
                r = xbi_returns[i]
            else:
                r = beta * xbi_returns[i] + rng.gauss(0, 0.028)
                jump = jumps[ticker].get(d)
                if jump is not None:
                    r += jump
                    drift_left, drift = 4, jump * 0.04  # small follow-through after news
                elif drift_left:
                    r += drift
                    drift_left -= 1
            price = max(0.5, price * (1 + r))
            volume = int(base_volume * rng.uniform(0.6, 1.4) * (6 if d in jumps.get(ticker, {}) else 1))
            p = Decimal(f"{price:.4f}")
            price_rows.append(Prices(security_id=sec.security_id, trade_date=d,
                                     close=p, adjusted_close=p, volume=volume))
    db.add_all(price_rows)
    db.commit()

    counts = {m.__tablename__: db.scalar(select(func.count()).select_from(m)) for m in reversed(DELETE_ORDER)}
    print("Seeded demo data:", ", ".join(f"{k}={v}" for k, v in counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="clear demo data, then seed")
    parser.add_argument("--clear", action="store_true", help="clear demo data only")
    parser.add_argument("--force", action="store_true", help="allow clearing even if real data exists")
    args = parser.parse_args()
    db = SESSION_LOCAL()
    try:
        if args.reset or args.clear:
            clear(db, args.force)
        if not args.clear:
            seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
