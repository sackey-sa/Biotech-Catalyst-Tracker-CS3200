"""events: derived from FDA approvals (openFDA + matching 8-K) and from manually entered press releases.

Timing rules (all times US/Eastern, using actual trading days from the XBI price history):
- before 16:00 on a trading day  -> that trading day (pre-market and intraday news moves that day)
- 16:00 or later, or a non-trading day -> the next trading day
FDA approvals carry only a date. If the company filed an 8-K on that date or the next day,
we use its acceptance timestamp and link it as evidence. Otherwise we assume the news came
after the close (16:00 ET), which puts the event on the next trading day.
"""
import bisect
import csv
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Events, FdaActions, Filings, Prices, Securities, Trials
from pipeline import config
from pipeline.loaders.common import company_ids_by_ticker

log = logging.getLogger(__name__)
ET = ZoneInfo(config.MARKET_TZ)
MARKET_CLOSE = time(16, 0)

EVENT_TYPES = {"fda_decision", "trial_readout"}
OUTCOMES = {"approved", "rejected", "positive", "negative", "mixed"}


class TradingCalendar:
    """Trading days taken from the benchmark's price history."""

    def __init__(self, session: Session):
        benchmark = config.BENCHMARK_TICKERS[0]
        q = (select(Prices.trade_date).join(Securities)
             .where(Securities.ticker == benchmark).order_by(Prices.trade_date))
        self.days = list(session.scalars(q))
        if not self.days:
            raise RuntimeError(f"No {benchmark} prices loaded; run the prices step before events.")

    def trading_day(self, ts_utc: datetime) -> date | None:
        """Trading day whose close-to-close return first reflects news at ts_utc."""
        local = ts_utc.replace(tzinfo=timezone.utc).astimezone(ET)
        d = local.date()
        idx = (bisect.bisect_right(self.days, d) if local.time() >= MARKET_CLOSE
               else bisect.bisect_left(self.days, d))
        return self.days[idx] if idx < len(self.days) else None


def et_to_utc(d: date, t: time) -> datetime:
    return datetime.combine(d, t, tzinfo=ET).astimezone(timezone.utc).replace(tzinfo=None)


def _save(session: Session, values: dict, existing: Events | None) -> bool:
    """Insert or update one event, skipping it if it would duplicate another event's
    (company_id, event_type, event_timestamp)."""
    clash = session.scalar(select(Events).where(
        Events.company_id == values["company_id"], Events.event_type == values["event_type"],
        Events.event_timestamp == values["event_timestamp"]))
    if clash is not None and clash is not existing:
        if existing is None and clash.fda_action_id is None and values.get("fda_action_id") is None:
            existing = clash  # manual re-entry of the same press release: update it
        else:
            log.warning("Skipping duplicate event %s (same company/type/time as event %s)",
                        values, clash.event_id)
            return False
    if existing is None:
        session.add(Events(**values))
    else:
        for k, v in values.items():
            setattr(existing, k, v)
    session.flush()
    return True


def load_fda_events(session: Session, cal: TradingCalendar) -> int:
    approvals = session.scalars(select(FdaActions).where(
        FdaActions.status == "AP", FdaActions.action_date >= config.START_DATE)).all()
    by_action = {e.fda_action_id: e for e in session.scalars(
        select(Events).where(Events.fda_action_id.is_not(None)))}
    n = 0
    for a in sorted(approvals, key=lambda a: (a.action_date, a.application_number)):
        # Earliest 8-K accepted on the action date (ET) or the following day.
        window = (et_to_utc(a.action_date, time(0)), et_to_utc(a.action_date + timedelta(days=2), time(0)))
        filing = session.scalar(
            select(Filings).where(Filings.company_id == a.company_id,
                                  Filings.form_type.like("8-K%"),
                                  Filings.acceptance_timestamp >= window[0],
                                  Filings.acceptance_timestamp < window[1])
            .order_by(Filings.acceptance_timestamp).limit(1))
        ts = filing.acceptance_timestamp if filing else et_to_utc(a.action_date, MARKET_CLOSE)
        day = cal.trading_day(ts)
        if day is None:
            continue
        values = {"company_id": a.company_id, "event_type": "fda_decision", "outcome": "approved",
                  "event_timestamp": ts, "trading_day": day, "nct_number": None,
                  "fda_action_id": a.fda_action_id,
                  "accession_number": filing.accession_number if filing else None,
                  "source_url": None}
        n += _save(session, values, by_action.get(a.fda_action_id))
    return n


def _parse_manual_timestamp(raw: str) -> datetime:
    """ISO 8601 with a time. No UTC offset means US/Eastern (press releases are dated in ET)."""
    if "T" not in raw and " " not in raw.strip():
        raise ValueError(f"event_timestamp {raw!r} needs a time of day, e.g. 2024-03-01T07:00")
    dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ET)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def load_manual_events(session: Session, cal: TradingCalendar) -> int:
    """Rows from data/manual_events.csv (trial readouts and FDA rejections from press releases)."""
    if not config.MANUAL_EVENTS_CSV.exists():
        return 0
    ids = company_ids_by_ticker(session)
    n = 0
    with open(config.MANUAL_EVENTS_CSV, newline="", encoding="utf-8") as f:
        for line_no, r in enumerate(csv.DictReader(f), start=2):
            r = {k: (v or "").strip() for k, v in r.items() if k}
            if not r.get("ticker"):
                continue
            where = f"{config.MANUAL_EVENTS_CSV.name} line {line_no}"
            try:
                company_id = ids.get(r["ticker"].upper())
                if company_id is None:
                    raise ValueError(f"unknown ticker {r['ticker']!r} (add it to companies.csv)")
                if r["event_type"] not in EVENT_TYPES:
                    raise ValueError(f"event_type must be one of {sorted(EVENT_TYPES)}")
                if r["outcome"] not in OUTCOMES:
                    raise ValueError(f"outcome must be one of {sorted(OUTCOMES)}")
                nct = r.get("nct_number") or None
                if nct and session.get(Trials, nct) is None:
                    raise ValueError(f"trial {nct} is not in the trials table")
                fda_action_id = None
                if r.get("application_number"):
                    fda_action_id = session.scalar(select(FdaActions.fda_action_id).where(
                        FdaActions.application_number == r["application_number"]))
                    if fda_action_id is None:
                        raise ValueError(f"application {r['application_number']} is not in fda_actions")
                if nct and fda_action_id:
                    raise ValueError("give nct_number or application_number, not both")
                accession = r.get("accession_number") or None
                if accession and session.get(Filings, accession) is None:
                    raise ValueError(f"filing {accession} is not in the filings table")
                if not (accession or r.get("source_url") or fda_action_id):
                    raise ValueError("needs a source_url or accession_number as evidence")

                ts = _parse_manual_timestamp(r["event_timestamp"])
                day = cal.trading_day(ts)
                if day is None:
                    raise ValueError("timestamp is after the last loaded trading day")
                values = {"company_id": company_id, "event_type": r["event_type"],
                          "outcome": r["outcome"], "event_timestamp": ts, "trading_day": day,
                          "nct_number": nct, "fda_action_id": fda_action_id,
                          "accession_number": accession, "source_url": r.get("source_url") or None}
                existing = (session.scalar(select(Events).where(Events.fda_action_id == fda_action_id))
                            if fda_action_id else None)
                n += _save(session, values, existing)
            except (KeyError, ValueError) as exc:
                log.error("%s: %s; row skipped", where, exc)
    return n


def load(session: Session) -> None:
    cal = TradingCalendar(session)
    fda = load_fda_events(session, cal)
    manual = load_manual_events(session, cal)
    session.commit()
    log.info("events: %d from FDA approvals, %d from manual press releases", fda, manual)
