"""Database helpers: bulk upsert that works on MySQL (and SQLite for local testing)."""
from sqlalchemy.orm import Session


def upsert(session: Session, model, rows: list[dict], key_cols: list[str], chunk: int = 1000) -> int:
    """Insert rows, updating non-key columns when the primary/unique key already exists."""
    if not rows:
        return 0
    dialect = session.get_bind().dialect.name
    if dialect == "mysql":
        from sqlalchemy.dialects.mysql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise NotImplementedError(f"upsert not implemented for {dialect}")

    update_cols = [c for c in rows[0] if c not in key_cols]
    for i in range(0, len(rows), chunk):
        stmt = insert(model).values(rows[i:i + chunk])
        if dialect == "mysql":
            if update_cols:
                stmt = stmt.on_duplicate_key_update({c: stmt.inserted[c] for c in update_cols})
            else:
                stmt = stmt.prefix_with("IGNORE")
        else:
            if update_cols:
                stmt = stmt.on_conflict_do_update(
                    index_elements=key_cols, set_={c: stmt.excluded[c] for c in update_cols})
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=key_cols)
        session.execute(stmt)
    return len(rows)
