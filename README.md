# Biotech-Catalyst-Tracker-CS3200

How do biotech stocks react to FDA decisions and clinical trial readouts? This project links
companies, their trials (ClinicalTrials.gov), FDA actions (openFDA), SEC filings (EDGAR) and daily
prices in MySQL, then measures each event's **abnormal return**: the stock's move minus the XBI
biotech index's move, from the close before the news.

## Layout

| Path | What it is |
|---|---|
| `models.py`, `database.py`, `datacreator.py` | SQLAlchemy schema, connection, table creation |
| `backend/` | FastAPI read-only API for the frontend |
| `backend/sql/views.sql` | `price_index` and `event_returns` views (the return calculations) |
| `backend/queries/*.sql` | The showcase queries; the frontend's SQL Showcase page runs these |
| `backend/seed_demo.py` | Fills the database with **fictional** demo data until the real loaders exist |
| `frontend/` | React + TypeScript app (Vite, React Router, TanStack Query, Recharts, Tailwind) |

## Setup (once)

Requires MySQL 8 running on `127.0.0.1:3306`, Python 3.12 and Node 20+.

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
echo "DB_PASSWORD=your-mysql-root-password" > .env
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS biotech_catalyst"
./venv/bin/python datacreator.py           # create the tables
./venv/bin/python -m backend.setup_views   # create the views (re-run after editing views.sql)
./venv/bin/python -m backend.seed_demo     # optional: fictional demo data
(cd frontend && npm install)
```

`seed_demo.py --reset` replaces the demo data and `--clear` removes it. Demo companies have CIKs
starting `999999`, and the app shows a "Demo data" badge while any are present.

## Run

Two terminals, from the repo root:

```bash
./venv/bin/uvicorn backend.main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. The API's interactive docs are at http://localhost:8000/docs.

## Pages

- **Dashboard**: headline numbers and the average reaction by outcome
- **Events**: every catalyst, with filters and sorting
- **Event detail**: stock vs XBI for 10 trading days either side, plus the trial or FDA action and the SEC filing
- **Companies / company profile**: price history with events marked, pipeline, FDA history, filings
- **Trials**: trials by phase, status and condition
- **SQL Showcase**: each graded query with its question, its SQL and a button that runs it live
