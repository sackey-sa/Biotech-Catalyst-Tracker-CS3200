"""Pull data from every source and populate the database.

    python run_pipeline.py                 # all steps, in order
    python run_pipeline.py trials prices   # only some steps
    python run_pipeline.py --create-tables # create tables first (same as datacreator.py)

Every step is safe to re-run: rows are upserted, never duplicated.
"""
import argparse
import logging

from database import SESSION_LOCAL, engine
from models import Base
from pipeline.loaders import companies, events, fda, filings, prices, trials

# Order matters: companies first (everything references company_id), events last
# (needs FDA actions, filings, and the price calendar).
STEPS = {
    "companies": companies.load,   # SEC CIK lookup -> companies, company_aliases, securities
    "filings": filings.load,       # SEC EDGAR 8-Ks
    "fda": fda.load,               # openFDA original applications -> fda_actions, drugs
    "trials": trials.load,         # ClinicalTrials.gov -> trials, conditions, drugs, join tables
    "prices": prices.load,         # yfinance daily prices (companies + XBI)
    "events": events.load,         # FDA approvals + data/manual_events.csv -> events
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("steps", nargs="*", help=f"steps to run (default: all): {', '.join(STEPS)}")
    parser.add_argument("--create-tables", action="store_true", help="run create_all before loading")
    parser.add_argument("--echo-sql", action="store_true", help="log every SQL statement")
    args = parser.parse_args()
    unknown = [s for s in args.steps if s not in STEPS]
    if unknown:
        parser.error(f"unknown step(s) {unknown}; choose from {list(STEPS)}")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    engine.echo = args.echo_sql

    if args.create_tables:
        Base.metadata.create_all(engine)

    for name in args.steps or STEPS:
        logging.info("=== %s ===", name)
        with SESSION_LOCAL() as session:
            STEPS[name](session)


if __name__ == "__main__":
    main()
