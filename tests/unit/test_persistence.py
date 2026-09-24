"""Unit tests for the SQL persistence primitives."""
from sqlalchemy import Column, Integer, MetaData, String, Table, select

from sdk.common.persistence import PlatformStore


def _kv_table():
    return Table(
        "kv_probe",
        MetaData(),
        Column("key", String(64), primary_key=True),
        Column("value", Integer, nullable=False),
    )


def test_boot_migration_is_idempotent():
    store = PlatformStore("sqlite:///:memory:")
    table = _kv_table()
    store.ensure_schema(table)
    store.ensure_schema(table)  # second boot must not raise
    with store.session() as s:
        s.execute(table.insert().values(key="a", value=1))
    with store.session() as s:
        assert s.execute(select(table.c.value).where(table.c.key == "a")).scalar() == 1


def test_session_rolls_back_on_error():
    store = PlatformStore("sqlite:///:memory:")
    table = _kv_table()
    store.ensure_schema(table)
    try:
        with store.session() as s:
            s.execute(table.insert().values(key="a", value=1))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with store.session() as s:
        assert s.execute(select(table)).all() == []


def test_healthcheck():
    assert PlatformStore("sqlite:///:memory:").healthcheck() is True
