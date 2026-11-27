"""Cleaning helpers shared by the source clients and loaders."""
import re
from datetime import date, datetime, timezone

# Legal suffixes and filler dropped when comparing company names across sources.
_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
             "llc", "plc", "sa", "ag", "nv", "the", "ma", "de"}
_ABBREVIATIONS = {"pharms": "pharmaceuticals", "pharm": "pharmaceutical",
                  "theraps": "therapeutics", "biosci": "biosciences"}


def name_key(name: str) -> str:
    """Comparable form of a company name: 'VERTEX PHARMS INC' -> 'vertex pharmaceuticals'."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    words = [_ABBREVIATIONS.get(w, w) for w in words if w not in _SUFFIXES]
    return " ".join(words)


def fold(text: str) -> str:
    """Case- and whitespace-insensitive key, matching MySQL's default collation behavior."""
    return " ".join(text.split()).casefold()


def clip(text: str | None, length: int) -> str | None:
    """Trim whitespace and cut to the column length."""
    if text is None:
        return None
    text = " ".join(text.split())
    return text[:length] if text else None


def parse_partial_date(value: str | None) -> date | None:
    """ClinicalTrials.gov dates are 'YYYY-MM-DD' or 'YYYY-MM'; month-only becomes the 1st."""
    if not value:
        return None
    parts = value.split("-")
    try:
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 1)
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_yyyymmdd(value: str | None) -> date | None:
    """openFDA dates look like '20191021'."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_utc(value: str | None) -> datetime | None:
    """ISO timestamp -> naive UTC datetime (the database stores UTC without tzinfo)."""
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


_PLACEBO = re.compile(r"\b(or |and |\+ )?(matching |matched )?placebo( to match)?\b", re.I)


def clean_intervention_name(name: str) -> str | None:
    """Drop placebo wording; return None if nothing is left ('Placebo', 'Matching placebo')."""
    cleaned = _PLACEBO.sub("", name)
    cleaned = cleaned.strip(" ,;/+-()")
    if not cleaned or cleaned.lower() in _NOT_A_DRUG:
        return None
    return cleaned


_NOT_A_DRUG = {"saline", "normal saline", "vehicle", "non-interventional", "no intervention",
               "none", "standard of care", "standard of care (soc)", "best supportive care"}
