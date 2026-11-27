"""Download and load historical stock prices from Yahoo Finance."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from math import isfinite

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from database import SESSION_LOCAL
from models import Prices, Securities


def load_ticker_prices(ticker: str, start: date, end: date) -> int:
    """
    Download daily historical prices and upsert them into the prices table.

    Args:
        ticker: Yahoo Finance ticker symbol (e.g. AAPL or XBI).
        start: First date to download (inclusive).
        end: Last date to download (exclusive).

    Returns:
        Number of price records processed.
    """
    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError("Ticker cannot be empty.")

    if start >= end:
        raise ValueError("Start date must be earlier than end date.")

    # Find the existing security record.
    with SESSION_LOCAL() as session:
        security_id = session.execute(
            select(Securities.security_id).where(
                Securities.ticker == ticker
            )
        ).scalar_one_or_none()

    if security_id is None:
        raise ValueError(
            f"{ticker} was not found in the securities table. "
            "Add the security before loading its prices."
        )

    # Download prices. Yahoo Finance treats end as exclusive.
    history = yf.Ticker(ticker).history(
        start=start.isoformat(),
        end=end.isoformat(),
        auto_adjust=False,
        actions=False,
    )

    if history.empty:
        print(f"No historical prices found for {ticker}.")
        return 0

    required_columns = {"Close", "Adj Close", "Volume"}
    missing_columns = required_columns - set(history.columns)

    if missing_columns:
        raise ValueError(
            f"Yahoo Finance did not return expected columns for {ticker}: "
            f"{missing_columns}"
        )

    records = []

    for timestamp, row in history.iterrows():
        close = row["Close"]
        adjusted_close = row["Adj Close"]
        volume = row["Volume"]

        # Skip incomplete price records.
        if not isfinite(float(close)) or not isfinite(float(adjusted_close)):
            continue

        if close <= 0 or adjusted_close <= 0:
            continue

        trade_date = timestamp.date()

        records.append({
            "security_id": security_id,
            "trade_date": trade_date,
            "close": Decimal(str(close)).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            ),
            "adjusted_close": Decimal(str(adjusted_close)).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            ),
            "volume": 0 if not isfinite(float(volume)) else int(volume),
        })

    if not records:
        print(f"No valid price records found for {ticker}.")
        return 0

    # Insert new records or update existing records with the same
    # security_id and trade_date.
    statement = mysql_insert(Prices).values(records)

    statement = statement.on_duplicate_key_update(
        close=statement.inserted.close,
        adjusted_close=statement.inserted.adjusted_close,
        volume=statement.inserted.volume,
    )

    with SESSION_LOCAL() as session:
        try:
            session.execute(statement)
            session.commit()
        except Exception:
            session.rollback()
            raise

    print(f"{ticker}: processed {len(records)} daily price records.")
    return len(records)


def load_multiple_tickers(tickers: list[str], start: date, end: date) -> int:
    """
    Download and load historical prices for multiple tickers.

    Args:
        tickers: List of Yahoo Finance ticker symbols.
        start: First date to download (inclusive).
        end: Last date to download (exclusive).

    Returns:
        Total number of price records processed across all tickers.
    """
    total_records: int = 0

    for ticker in tickers:
        try:
            count = load_ticker_prices(ticker, start, end)
            total_records += count
        except ValueError as error:
            print(f"Could not load {ticker}: {error}")

    print(f"\nTotal records processed across all tickers: {total_records}")
    return total_records
