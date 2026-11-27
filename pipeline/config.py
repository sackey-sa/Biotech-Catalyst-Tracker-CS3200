"""Settings shared by every pipeline step. Override with environment variables (or .env)."""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COMPANIES_CSV = DATA_DIR / "companies.csv"
MANUAL_EVENTS_CSV = DATA_DIR / "manual_events.csv"

# Earliest date for filings, prices, and events. Trials and FDA actions are loaded in full.
START_DATE = date.fromisoformat(os.getenv("PIPELINE_START_DATE", "2015-01-01"))

# Benchmark ETF stored in securities with company_id NULL.
BENCHMARK_TICKERS = ["XBI"]

# SEC requires a User-Agent that identifies you, e.g. "Your Name your.email@northeastern.edu".
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "")

# Generic User-Agent for the APIs that don't need contact details.
DEFAULT_USER_AGENT = "biotech-catalyst-tracker/1.0 (CS3200 course project)"

# 8-K forms to load from EDGAR.
FILING_FORMS = {"8-K", "8-K/A"}

# Intervention types from ClinicalTrials.gov that count as drugs.
DRUG_INTERVENTION_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}

MARKET_TZ = "America/New_York"
