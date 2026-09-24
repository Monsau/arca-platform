"""SQL persistence primitives shared by platform services and adapters.

One engine per store with an idempotent boot migration
(`CREATE TABLE IF NOT EXISTS` semantics via `checkfirst=True`) and a
commit-on-success session context manager. SQLite is accepted for
development and tests; PostgreSQL is the production target. An in-memory
mode remains available for tests through `sqlite:///:memory:` or the
dedicated in-memory stores in the adapters.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Table, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class PlatformStore:
    """Minimal SQL store: engine + idempotent schema migration + sessions."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        kwargs: dict = {}
        if database_url.startswith("sqlite") and ":memory:" in database_url:
            # One shared in-memory database: without StaticPool each pooled
            # connection (e.g. from the TestClient portal thread) would get a
            # fresh, empty SQLite database and boot-migrated tables would
            # "disappear" between requests.
            kwargs["poolclass"] = StaticPool
            kwargs["connect_args"] = {"check_same_thread": False}
        self.engine = create_engine(database_url, **kwargs)
        self._sessionmaker = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Commit on success, rollback on error, always close."""
        session = self._sessionmaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ensure_schema(self, *tables: Table) -> None:
        """Idempotent boot migration — safe to run on every startup."""
        for table in tables:
            table.create(self.engine, checkfirst=True)

    def healthcheck(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
