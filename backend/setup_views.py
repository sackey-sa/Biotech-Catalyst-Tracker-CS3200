"""Create (or refresh) the backend-only views in backend/sql/views.sql.

Run from the repo root:  python -m backend.setup_views

Only price_index and event_windows may be created here. The team's event_returns
view lives in sql/02_calculations.sql and must be run in Workbench (it uses
DELIMITER, which only the MySQL clients understand).
"""
import re
import sys

from sqlalchemy import text

from backend.db import BACKEND_DIR, engine

ALLOWED_VIEWS = ("price_index", "event_windows")
VIEW_NAME = re.compile(r"^\s*CREATE\s+OR\s+REPLACE\s+VIEW\s+`?(\w+)`?\s+AS\b", re.IGNORECASE)


def load_statements() -> list[tuple[str, str]]:
    """Return (view_name, sql) pairs, refusing anything but the allowed views."""
    sql = (BACKEND_DIR / "sql" / "views.sql").read_text()
    # Strip comment lines, then split on ';' into individual statements.
    body = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    statements = [s.strip() for s in body.split(";") if s.strip()]
    checked = []
    for stmt in statements:
        match = VIEW_NAME.match(stmt)
        if not match or match.group(1).lower() not in ALLOWED_VIEWS:
            sys.exit("views.sql may only contain CREATE OR REPLACE VIEW for "
                     f"{', '.join(ALLOWED_VIEWS)}. Refusing to run:\n{stmt[:200]}")
        checked.append((match.group(1), stmt))
    return checked


def main() -> None:
    statements = load_statements()  # validate everything before touching the database
    with engine.begin() as conn:
        for _, stmt in statements:
            conn.execute(text(stmt))
        has_team_view = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.VIEWS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'event_returns'")).scalar()
    print("Applied views: " + ", ".join(name for name, _ in statements))
    if not has_team_view:
        print("WARNING: event_returns is missing. Run sql/02_calculations.sql in Workbench "
              "before starting the API.")


if __name__ == "__main__":
    main()
