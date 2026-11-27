"""Yahoo Finance (via yfinance): daily close, adjusted close, and volume."""
import math
from datetime import date

import yfinance as yf


def daily_prices(ticker: str, since: date) -> list[dict]:
    """One dict per trading day from `since` through today."""
    hist = yf.Ticker(ticker).history(start=since.isoformat(), auto_adjust=False, actions=False)
    rows = []
    for ts, r in hist.iterrows():
        close, adj, vol = r.get("Close"), r.get("Adj Close"), r.get("Volume")
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (close, adj, vol)):
            continue
        rows.append({
            "trade_date": ts.date(),  # index is midnight America/New_York, so .date() is the trading day
            "close": round(float(close), 4),
            "adjusted_close": round(float(adj), 4),
            "volume": int(vol),
        })
    return rows
