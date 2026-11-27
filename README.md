# Biotech-Catalyst-Tracker-CS3200

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the repo root:

```
DB_PASSWORD=your_mysql_root_password
SEC_USER_AGENT=Your Name your.email@northeastern.edu   # SEC requires a name + email
# optional
PIPELINE_START_DATE=2015-01-01   # earliest date for filings, prices, and events
DATABASE_URL=sqlite:///test.db   # use a different DB instead of local MySQL
```

## Loading data

```bash
python run_pipeline.py --create-tables   # create tables and run every step
python run_pipeline.py trials prices     # run only some steps
```

Steps run in this order. Each one is safe to re-run because rows are upserted, never duplicated.

| Step | Source | Tables |
|---|---|---|
| `companies` | `data/companies.csv` + SEC ticker→CIK lookup | companies, company_aliases, securities (incl. XBI) |
| `filings` | SEC EDGAR submissions API | filings (8-K, 8-K/A) |
| `fda` | openFDA drugsfda (ORIG submissions only) | fda_actions, drugs |
| `trials` | ClinicalTrials.gov API v2 (by lead sponsor) | trials, conditions, trial_conditions, drugs, trial_drugs |
| `prices` | yfinance | prices |
| `events` | FDA approvals + `data/manual_events.csv` | events |

### Code layout

- `pipeline/sources/`: one API client per source. They return plain dicts and contain no database code.
- `pipeline/loaders/`: map API output to `company_id` and write it to the tables.
- `pipeline/normalize.py`: name, date, and intervention cleaning.

### Adding companies

Add a row to `data/companies.csv`:

- `ctgov_sponsors`: the lead-sponsor search term for ClinicalTrials.gov.
- `openfda_prefixes`: the first word of the openFDA `sponsor_name`, e.g. `VERTEX` matches "VERTEX PHARMS INC".

Use `|` to separate multiple values. Every spelling seen in a source is recorded in `company_aliases`.

### Manual events (press releases)

`data/manual_events.csv` holds trial readouts and FDA rejections, which the APIs don't provide. One row per event:

| column | notes |
|---|---|
| `ticker` | must be in companies.csv |
| `event_type` | `trial_readout` or `fda_decision` |
| `outcome` | `approved`, `rejected`, `positive`, `negative`, `mixed` |
| `event_timestamp` | ISO time from the press release, e.g. `2024-02-05T07:00`. No offset means US/Eastern. A time of day is required. |
| `nct_number` / `application_number` | optional subject (at most one), must already be loaded |
| `accession_number` / `source_url` | evidence (at least one) |

### Event timing

Timestamps are stored in UTC. `trading_day` is the first trading day (from XBI price history) whose close reflects the news:

- before 16:00 ET on a trading day → that day
- at or after 16:00 ET, or on a weekend or holiday → the next trading day

openFDA gives approval dates without times. The pipeline uses the acceptance time of the company's first 8-K filed that day or the next day, and links it as evidence. If there is no such 8-K, it assumes 16:00 ET, which puts the event on the next trading day.

### Known limitations

- openFDA drugsfda leaves out vaccines and other CBER biologics, and it has no rejections (CRLs). Enter those manually.
- Two approvals for the same company at the same timestamp collapse to one event, because of the `no_duplicate_events` constraint. A warning is logged.
- Trial intervention names are stored as ClinicalTrials.gov reports them, apart from placebo filtering.
