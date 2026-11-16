"""
LOAD: write the clean tables into a database.

Two environments:
  local    -> a SQLite file on your computer (data/athletes_local.db). Safe for practice.
  supabase -> your Supabase (PostgreSQL) database. Needs DATABASE_URL in a .env file.

Safety: each table is replaced inside ONE transaction.
If anything goes wrong halfway, the database rolls back and keeps the old data.
Every run is also recorded in a 'pipeline_runs' table (monitoring).
"""
import json
import logging
import os
import sqlite3
from datetime import date, datetime, timezone

import pandas as pd

import config

log = logging.getLogger("pipeline.load")

SQL_TYPES = {
    "sqlite":   {"text": "TEXT", "int": "INTEGER", "float": "REAL", "date": "TEXT"},
    "postgres": {"text": "text", "int": "bigint", "float": "double precision", "date": "date"},
}
ID_COLUMN = {
    "sqlite":   "id INTEGER PRIMARY KEY AUTOINCREMENT",
    "postgres": "id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
}
PLACEHOLDER = {"sqlite": "?", "postgres": "%s"}


# ------------------------------------------------------------------
# Connecting
# ------------------------------------------------------------------
def read_env_file(path=".env"):
    """Read KEY=value lines from .env into environment variables (keeps secrets out of the code)."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def connect(environment: str):
    """Return (connection, dialect) for 'local' or 'supabase'."""
    if environment == "local":
        os.makedirs(os.path.dirname(config.LOCAL_DB), exist_ok=True)
        log.info("Connecting to local database %s", config.LOCAL_DB)
        return sqlite3.connect(config.LOCAL_DB), "sqlite"

    if environment == "supabase":
        read_env_file()
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and paste your "
                               "Supabase connection string.")
        import psycopg                      # only needed for Supabase
        log.info("Connecting to Supabase")
        return psycopg.connect(url), "postgres"

    raise ValueError(f"Unknown environment: {environment}")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def create_table_sql(table: str, dialect: str) -> str:
    types = SQL_TYPES[dialect]
    cols = [ID_COLUMN[dialect]] + [f"{c} {types[t]}" for c, t in config.SCHEMAS[table].items()]
    return f"CREATE TABLE IF NOT EXISTS {table} (\n  " + ",\n  ".join(cols) + "\n)"


def python_value(value, dialect):
    """Turn pandas/numpy values into plain Python values the database understands."""
    if value is None or (not isinstance(value, (str, date)) and pd.isna(value)):
        return None                                   # NaN / <NA> -> NULL
    if isinstance(value, date):
        return value.isoformat() if dialect == "sqlite" else value
    if hasattr(value, "item"):
        return value.item()                           # numpy int/float -> Python int/float
    return value


def rows_for_insert(df: pd.DataFrame, dialect: str) -> list:
    return [tuple(python_value(v, dialect) for v in row)
            for row in df.itertuples(index=False, name=None)]


# ------------------------------------------------------------------
# Loading
# ------------------------------------------------------------------
def replace_table(conn, dialect: str, table: str, df: pd.DataFrame):
    """Delete old rows and insert new ones in ONE transaction (all or nothing)."""
    columns = list(config.SCHEMAS[table])
    marks = ", ".join([PLACEHOLDER[dialect]] * len(columns))
    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})"

    cur = conn.cursor()
    try:
        cur.execute(create_table_sql(table, dialect))
        if dialect == "postgres":                     # keep the public API locked (RLS on)
            cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        cur.execute(f"DELETE FROM {table}")
        cur.executemany(insert_sql, rows_for_insert(df, dialect))
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        if count != len(df):                          # verify everything arrived
            raise RuntimeError(f"{table}: expected {len(df)} rows, database has {count}")
        conn.commit()
        log.info("Loaded %s: %d rows", table, count)
        return count
    except Exception:
        conn.rollback()
        log.error("Load of %s failed; rolled back, old data kept", table)
        raise


def record_run(conn, dialect, run: dict):
    """Save one row about this run into pipeline_runs (when it ran, status, rows, warnings)."""
    text = "TEXT" if dialect == "sqlite" else "text"
    cur = conn.cursor()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS pipeline_runs (
        run_id {text}, environment {text}, started_at {text}, finished_at {text},
        status {text}, rows_loaded {text}, warnings INTEGER, message {text})""")
    if dialect == "postgres":
        cur.execute("ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY")
    p = PLACEHOLDER[dialect]
    cur.execute(f"INSERT INTO pipeline_runs VALUES ({', '.join([p] * 8)})", (
        run["run_id"], run["environment"], run["started_at"],
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        run["status"], json.dumps(run.get("rows_loaded", {})),
        run.get("warnings", 0), run.get("message", ""),
    ))
    conn.commit()


def load_all(conn, dialect, tables: dict) -> dict:
    return {name: replace_table(conn, dialect, name, df) for name, df in tables.items()}
