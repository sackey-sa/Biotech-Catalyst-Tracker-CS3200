# Biotech Catalyst Tracker (CS 3200, Group 21)

MySQL database linking clinical trials, FDA actions, SEC filings, and daily
prices for biotech companies. It measures how much each company's stock moved
because of its own news:

    abnormal return = stock's move - XBI's move on the event's trading day

XBI is a biotech sector fund, used as the benchmark.

## Project context
- CS 3200 group project (Group 21). Graded 25% each on motivation,
  presentation, database design, and functionality.
- Deliverables: group21_queries_and_output.pdf (5 or 6 graded queries with
  their output), group21_presentation.pdf (5–6 slides incl. EER diagram),
  code zip, database backup (mysqldump).
- Scope: about 20 small and mid-size public biotechs. FDA approvals first,
  then trial readouts and rejections from press releases. Keep data
  pulls small.
- Ownership: Sam (ClinicalTrials.gov, openFDA loaders), Eftyghia (prices,
  press-release events), Aaron (events builder, EDGAR loader), Shaan and
  Rayn (frontend), Abdullah (company list, calculations, queries).
  Don't rewrite another person's loader without asking.
- Graded queries must have joins and/or subqueries, a plain-English
  question, and tests in sql/04_tests.sql.

## Repo layout
- `models.py`: the 12 tables (SQLAlchemy). The schema is final.
- `database.py`: engine and `SESSION_LOCAL`; reads `DB_PASSWORD` from `.env`.
- `datacreator.py`: creates the tables (`Base.metadata.create_all`).
- `sql/01_test_data.sql`: fake test data. Test databases only.
- `sql/02_calculations.sql`: `daily_return` function, `event_returns` view,
  `compute_abnormal_returns` procedure. Uses DELIMITER, so run it in
  Workbench or the mysql client, never through SQLAlchemy.
- `sql/03_queries.sql`: all queries. Each starts with `-- QUERY N`, `-- title:`,
  `-- question:`, `-- graded: yes|no`. Only `graded: yes` queries go in the
  queries PDF (5 or 6 total).
- `sql/04_tests.sql`: checks against hand-worked answers. Must print all PASS.
- `backend/`: FastAPI read-only API. `backend/sql/views.sql` holds the
  backend-only views (`price_index`, `event_windows`).
- `frontend/`: React + TypeScript app (Vite).
- `docs/`: EER diagram and presentation.

## The 12 tables
companies, company_aliases, securities, prices, drugs, conditions, trials,
trial_conditions, trial_drugs, fda_actions, filings, events.

- Ticker lives only in `securities`. XBI is a security with no company.
- `events` is built from the other tables, never pulled from an API.
- An event is about at most one subject (`nct_number` or `fda_action_id`) and
  needs evidence (`accession_number`, `source_url`, or an FDA action).
- `event_type` is `fda_decision` or `trial_readout`. `outcome` is approved,
  rejected, positive, negative, or mixed.
- No duplicate events; each FDA action creates at most one event.

## Rules
- Don't change `models.py`. Schema changes need a team decision.
- Don't change `sql/01`, `sql/02`, or `sql/04` unless the task says so.
- Never load `backend/seed_demo.py` and `sql/01_test_data.sql` into the same
  database.
- Never read, print, or commit `.env`. Never hard-code passwords or keys.
- One branch per task. Small commits with clear messages.

## How to work
Go one step at a time:
1. Plan the step and wait for approval.
2. Make the change.
3. Run the step's checks.
4. Commit.
5. Report results and stop until told to continue.
If you can't run a check yourself, give the exact commands and wait.

## Test databases
- Test DB: fresh database, `datacreator.py`, `sql/01_test_data.sql`,
  `sql/02_calculations.sql`. Then `sql/04_tests.sql` must show all PASS.
- Demo DB: fresh database, `datacreator.py`, `sql/02_calculations.sql`,
  `python -m backend.setup_views`, `python -m backend.seed_demo`. Every app
  page must load.

## Environment
- Windows, PowerShell. Activate with `.\venv\Scripts\Activate.ps1`.
- MySQL 8 on localhost:3306, user root, database `biotech_catalyst`.
- In PowerShell, quote git stash names: `git stash pop 'stash@{1}'`.

## Data conventions
- IDs (NCT, application, accession, CIK) are strings. CIK is 10 digits,
  zero-padded.
- Calendar dates are DATE; timestamps are DATETIME in UTC.
- Trading day: convert UTC to America/New_York. News at or after 4pm counts
  toward the next trading day. A trading day is a date with an XBI price.
- Returns use `adjusted_close`.
- openFDA: original applications only, no supplements.
- SEC EDGAR requests send `SEC_USER_AGENT` from `.env`; stay under 10/second.


- No mysql command-line client. SQL files in sql/ are run by the user in
  Workbench; ask the user to run them and paste back the output.