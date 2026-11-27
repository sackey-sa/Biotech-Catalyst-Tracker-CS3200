"""SEC EDGAR: ticker -> CIK lookup and 8-K filings with acceptance timestamps.

EDGAR asks for at most 10 requests/second and a User-Agent naming who you are.
acceptanceDateTime in the submissions JSON is real UTC (16:05 ET earnings 8-Ks show
as 21:05Z in winter and 20:05Z in summer).
"""
from datetime import date

from pipeline import config
from pipeline.http import ApiClient
from pipeline.normalize import parse_utc

_client: ApiClient | None = None


def _sec() -> ApiClient:
    global _client
    if _client is None:
        if not config.SEC_USER_AGENT or "@" not in config.SEC_USER_AGENT:
            raise RuntimeError(
                "Set SEC_USER_AGENT in .env to your name and email, "
                "e.g. SEC_USER_AGENT=\"Jane Doe jane@northeastern.edu\" (SEC requires it).")
        _client = ApiClient("https://data.sec.gov", config.SEC_USER_AGENT, min_interval=0.12)
    return _client


def ticker_map() -> dict[str, dict]:
    """{'VRTX': {'cik': '0000875320', 'title': 'VERTEX PHARMACEUTICALS INC / MA'}, ...}"""
    data = _sec().get("https://www.sec.gov/files/company_tickers.json")
    return {row["ticker"].upper(): {"cik": f"{int(row['cik_str']):010d}", "title": row["title"]}
            for row in data.values()}


def _rows_from_block(block: dict, cik: str, forms: set[str], since: date) -> list[dict]:
    rows = []
    for i, form in enumerate(block.get("form", [])):
        if form not in forms:
            continue
        filing_date = date.fromisoformat(block["filingDate"][i])
        if filing_date < since:
            continue
        rows.append({
            "accession_number": block["accessionNumber"][i],
            "cik": cik,
            "form_type": form,
            "filing_date": filing_date,
            "acceptance_timestamp": parse_utc(block["acceptanceDateTime"][i]),
        })
    return rows


def filings(cik: str, forms: set[str] = config.FILING_FORMS,
            since: date = config.START_DATE) -> list[dict]:
    """All filings of the given forms for one company, newest first, including older archive pages."""
    sub = _sec().get(f"submissions/CIK{cik}.json")
    rows = _rows_from_block(sub["filings"]["recent"], cik, forms, since)
    for page in sub["filings"].get("files", []):
        if date.fromisoformat(page["filingTo"]) < since:
            continue
        rows += _rows_from_block(_sec().get(f"submissions/{page['name']}"), cik, forms, since)
    return rows
