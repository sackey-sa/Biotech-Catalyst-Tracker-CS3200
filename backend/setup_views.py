"""Create (or refresh) the SQL views in backend/sql/views.sql.

Run from the repo root:  python -m backend.setup_views
"""
from sqlalchemy import text

from backend.db import BACKEND_DIR, engine


def main() -> None:
    sql = (BACKEND_DIR / "sql" / "views.sql").read_text()
    # Strip comment lines, then split on ';' into individual statements.
    body = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    statements = [s.strip() for s in body.split(";") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print(f"Applied {len(statements)} view statements.")


if __name__ == "__main__":
    main()
