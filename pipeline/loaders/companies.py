"""companies, company_aliases, securities: built from data/companies.csv plus SEC CIK lookups."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Companies, Securities
from pipeline import config
from pipeline.loaders.common import AliasRegistry, read_seed_companies
from pipeline.sources import sec_edgar

log = logging.getLogger(__name__)


def _upsert_security(session: Session, ticker: str, company_id: int | None, kind: str) -> None:
    sec = session.scalar(select(Securities).where(Securities.ticker == ticker))
    if sec is None:
        session.add(Securities(ticker=ticker, company_id=company_id, type=kind))
    else:
        sec.company_id, sec.type = company_id, kind


def load(session: Session) -> None:
    seeds = read_seed_companies()
    tickers = sec_edgar.ticker_map()
    aliases = AliasRegistry(session)

    for seed in seeds:
        info = tickers.get(seed.ticker)
        if info is None:
            log.warning("Ticker %s not found in SEC company_tickers.json; skipping", seed.ticker)
            continue
        company = session.scalar(select(Companies).where(Companies.cik == info["cik"]))
        if company is None:
            company = Companies(name=seed.name, cik=info["cik"])
            session.add(company)
            session.flush()
        else:
            company.name = seed.name

        aliases.add(seed.name, company.company_id, "seed")
        aliases.add(info["title"], company.company_id, "sec_edgar")
        _upsert_security(session, seed.ticker, company.company_id, "stock")
        log.info("Company %s -> id %s (CIK %s)", seed.ticker, company.company_id, info["cik"])

    for ticker in config.BENCHMARK_TICKERS:
        _upsert_security(session, ticker, None, "etf")
    session.commit()
