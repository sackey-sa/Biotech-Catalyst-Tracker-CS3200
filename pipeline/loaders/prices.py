"""prices: daily bars from yfinance for every security (company stocks and the XBI benchmark)."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Prices, Securities
from pipeline import config
from pipeline.db_utils import upsert
from pipeline.sources import prices as yahoo

log = logging.getLogger(__name__)


def load(session: Session) -> None:
    # Full refresh from START_DATE each run: adjusted_close is restated after splits/dividends.
    for sec in session.scalars(select(Securities)).all():
        rows = [{"security_id": sec.security_id, **r} for r in yahoo.daily_prices(sec.ticker, config.START_DATE)]
        if not rows:
            log.warning("%s: no price data returned", sec.ticker)
            continue
        upsert(session, Prices, rows, ["security_id", "trade_date"])
        session.commit()
        log.info("%s: %d price rows", sec.ticker, len(rows))
