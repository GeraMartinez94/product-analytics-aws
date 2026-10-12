"""Tests de calidad de datos sobre la capa curated. Correr despues de run_pipeline.py."""
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(f"CREATE VIEW events AS SELECT * FROM "
              f"read_parquet('{ROOT}/data/curated/events/*/*.parquet', hive_partitioning=true)")
    return c


def test_no_nulls_in_keys(con):
    n = con.execute("SELECT COUNT(*) FROM events WHERE event_id IS NULL OR user_id IS NULL").fetchone()[0]
    assert n == 0


def test_event_id_is_unique(con):
    n = con.execute("SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM events").fetchone()[0]
    assert n == 0


def test_event_names_in_catalog(con):
    n = con.execute("""SELECT COUNT(*) FROM events WHERE event_name NOT IN
        ('signup','onboarding_complete','feature_used','add_to_cart','purchase','session_start')""").fetchone()[0]
    assert n == 0


def test_funnel_is_monotonic(con):
    rows = con.execute((ROOT / "sql/01_funnel.sql").read_text()).fetchall()
    users = [r[2] for r in rows]
    assert users == sorted(users, reverse=True)
