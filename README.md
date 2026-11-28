# Biotech-Catalyst-Tracker-CS3200

How do biotech stocks react to FDA decisions and clinical trial readouts? This project links
companies, their trials (ClinicalTrials.gov), FDA actions (openFDA), SEC filings (EDGAR) and daily
prices in MySQL, then measures each event's **abnormal return**: the stock's move minus the XBI
biotech index's move, from the close before the news.

## Layout

| Path | What it is |
|---|---|
| `models.py`, `database.py`, `datacreator.py` | SQLAlchemy schema (12 tables), connection, table creation |
| `sql/01_test_data.sql` | Small fake data set with hand-worked answers. **Test databases only** |
| `sql/02_calculations.sql` | `daily_return` function, `event_returns` view, `compute_abnormal_returns` procedure |
| `sql/03_queries.sql` | Every query. `graded: yes` ones go in the queries PDF; the SQL Showcase page shows all of them |
| `sql/04_tests.sql` | Checks against the hand-worked answers. Every row must say PASS |
| `backend/` | FastAPI read-only API for the frontend |
| `backend/sql/views.sql` | Backend-only views: `price_index` and `event_windows` (5-day returns) |
| `backend/seed_demo.py` | Fills the database with **fictional** demo data until the real loaders exist |
| `frontend/` | React + TypeScript app (Vite, React Router, TanStack Query, Recharts, Tailwind) |
| `docs/eer.png`, `docs/presentation.pdf` | EER diagram and presentation |
| `CLAUDE.md` | Team rules, conventions and how we work |

## Requirements

- MySQL 8 running on `127.0.0.1:3306` (user `root`)
- **MySQL Workbench** (you run the files in `sql/` with it)
- Python 3.12
- Node 20 or newer

## Setup (once)

Run these from the repo folder. On Windows the commands call `.\venv\Scripts\python.exe`
directly, so you don't need to activate the venv (PowerShell often blocks `Activate.ps1`).

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Content -Path .env -Value "DB_PASSWORD=your-mysql-root-password" -Encoding ascii
cd frontend
npm install
cd ..
```

**Mac / Linux**

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
printf 'DB_PASSWORD=your-mysql-root-password\n' > .env
(cd frontend && npm install)
```

About `.env`:

- It holds your MySQL root password and is never committed (it's in `.gitignore`).
- If the password contains `#`, spaces or quotes, wrap it in single quotes:
  `DB_PASSWORD='p@ss#word'`.
- On Windows, don't create it with `echo ... > .env`: Windows PowerShell 5.1 writes UTF-16 by
  default, and Python then fails with `UnicodeDecodeError`. Use the `Set-Content` line above or
  any text editor (saved as UTF-8).
- Without `DB_PASSWORD` the app stops with `DB_PASSWORD is not set`.

Then create a database. See [Databases](#databases) for which data to load.

## The `sql/` files

Run them **in Workbench**, in this order: **01 → 02 → 03 → 04**. Open a file, then click
**Execute All** (the plain lightning bolt).

| File | What it does | When |
|---|---|---|
| `01_test_data.sql` | Loads 3 fake companies and 6 events | Test DB only |
| `02_calculations.sql` | Creates `daily_return`, `event_returns` and `compute_abnormal_returns` | **Every database, before the app starts** |
| `03_queries.sql` | Runs all queries, each with its question; Queries 1–6 have "Expected with test data" comments | Any time after 02 |
| `04_tests.sql` | Prints one row per check | Test DB only; all rows must say **PASS** |

> **`sql/02_calculations.sql` must be run in Workbench (or the `mysql` client) before the app
> starts.** It uses `DELIMITER`, which only the MySQL clients understand, so Python can't run it.
> The app needs its `event_returns` view; without it, `setup_views` prints a warning and most
> pages fail.

**Running the tests:**

1. Make a Test DB (below).
2. Run `sql/04_tests.sql`. All 10 rows must say **PASS**.

Queries 7 and 10 in `03_queries.sql` also use the backend's `event_windows` view, so on a
Test DB run `setup_views` (see [Demo DB](#databases), step 4, first command only) before running
the whole file.

## Databases

Everything uses one database called `biotech_catalyst`. Fill it with **one** kind of data:

| | Test DB | Demo DB |
|---|---|---|
| Data | `sql/01_test_data.sql`: 3 companies, 6 events | `backend/seed_demo.py`: 8 fictional companies, 2 years of prices |
| For | `04_tests.sql` and checking queries by hand | Trying the app with realistic-looking data |

> **Never load `seed_demo.py` and `sql/01_test_data.sql` into the same database.**
> `04_tests.sql` expects only the test data (it uses fixed IDs, like XBI = security 3), and both
> create an XBI security. `seed_demo.py` refuses to run if the database already has companies.

**Start fresh** (in Workbench) before switching between them:

```sql
DROP DATABASE IF EXISTS biotech_catalyst;
CREATE DATABASE biotech_catalyst;
```

**Test DB**

1. Start fresh (above).
2. Create the tables: `.\venv\Scripts\python.exe datacreator.py` (Mac/Linux: `./venv/bin/python datacreator.py`)
3. In Workbench, run `sql/01_test_data.sql`, then `sql/02_calculations.sql`.
4. In Workbench, run `sql/04_tests.sql`. All rows must say PASS.

**Demo DB**

1. Start fresh (above).
2. Create the tables: `.\venv\Scripts\python.exe datacreator.py`
3. In Workbench, run `sql/02_calculations.sql`. Its last line shows an empty report; that's fine.
4. Create the backend views and load the demo data:

   ```powershell
   .\venv\Scripts\python.exe -m backend.setup_views
   .\venv\Scripts\python.exe -m backend.seed_demo
   ```

   Mac/Linux: `./venv/bin/python -m backend.setup_views` and `./venv/bin/python -m backend.seed_demo`

`seed_demo.py --reset` replaces the demo data and `--clear` removes it. Demo companies have CIKs
starting `999999`, and the app shows a "Demo data" badge while any are present.

Re-run `setup_views` after editing `backend/sql/views.sql`. It only creates `price_index` and
`event_windows`, and never touches the team's `event_returns`.

## Run the app

Two terminals, both starting in the repo folder.

**Terminal 1, the API**

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Mac/Linux: `./venv/bin/uvicorn backend.main:app --reload --port 8000`

**Terminal 2, the website**

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. The API's interactive docs are at http://localhost:8000/docs.
Stop either one with Ctrl+C.

In PyCharm, the **Full stack** run configuration (in `.run/`) starts both.

## Pages

- **Dashboard**: headline numbers and the average reaction by outcome
- **Events**: every catalyst, with filters and sorting
- **Event detail**: stock vs XBI for 10 trading days either side, plus the trial or FDA action and the SEC filing
- **Companies / company profile**: price history with events marked, pipeline, FDA history, filings
- **Trials**: trials by phase, status and condition
- **SQL Showcase**: every query in `sql/03_queries.sql`, graded ones first, each with its question,
  its SQL and a button that runs it live

## Troubleshooting

- **`WARNING: event_returns is missing`** from `setup_views`, or pages show errors: run
  `sql/02_calculations.sql` in Workbench.
- **"Couldn't load this data. Unexpected token '<'"** on every page: the website can't reach the
  API. Check that Terminal 1 is running. If you switched git branches while `npm run dev` was
  running, stop it with Ctrl+C and start it again.
- **`address already in use`** or **`only one usage of each socket address`**: an old API or
  website is still running. Close its terminal, or stop the process using port 8000 or 5173.
- **`DB_PASSWORD is not set`**: create `.env` in the repo folder (see Setup).
- **`Access denied for user 'root'`**: the password in `.env` is wrong.
