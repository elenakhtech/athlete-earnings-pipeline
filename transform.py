"""
TRANSFORM: turn raw files into clean tables.

Each function takes a DataFrame and returns a cleaned DataFrame.
They don't download or save anything, so they're easy to test.
"""
import logging

import pandas as pd

import config

log = logging.getLogger("pipeline.transform")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make column names lowercase with no extra spaces: 'Total Earnings ' -> 'total_earnings'."""
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def trim_text(df: pd.DataFrame) -> pd.DataFrame:
    """Remove spaces at the start/end of every text value ('  Federer ' -> 'Federer')."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].str.strip()
    return df


def fix_names(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Replace known misspellings using config.NAME_CORRECTIONS."""
    df = df.copy()
    wrong = df[column].isin(config.NAME_CORRECTIONS.keys())
    if wrong.any():
        log.info("Fixing %d misspelled name(s) in '%s'", wrong.sum(), column)
    df[column] = df[column].replace(config.NAME_CORRECTIONS)
    return df


def fix_f1_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Formula 1 drivers labeled 'NASCAR' -> 'F1 Racing'."""
    df = df.copy()
    wrong = df["name"].isin(config.F1_DRIVERS) & (df["sport"] == "NASCAR")
    if wrong.any():
        log.info("Relabeling %d F1 driver row(s) from NASCAR to F1 Racing", wrong.sum())
    df.loc[wrong, "sport"] = "F1 Racing"
    return df


def to_whole_numbers(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Store whole-number columns as integers that can still be empty (Int64)."""
    df = df.copy()
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
    return df


# ------------------------------------------------------------------
# One function per source table
# ------------------------------------------------------------------
def transform_forbes(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = standardize_columns(df)
    df = trim_text(df)
    df = fix_f1_labels(df)
    df = to_whole_numbers(df, ["current_rank", "year"])
    return df[list(config.SCHEMAS["forbes_athletes"])]


def transform_earnings(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = standardize_columns(df)
    df = trim_text(df)
    df = fix_names(df, "player")
    df = to_whole_numbers(df, ["year", "earnings_rank"])
    return df[list(config.SCHEMAS["athlete_earnings"])]


def transform_tennis(path: str) -> pd.DataFrame:
    df = pd.read_sas(path, encoding="latin1")
    df = standardize_columns(df)
    df = trim_text(df)
    df = fix_names(df, "player")
    int_columns = [c for c, t in config.SCHEMAS["tennis_stats"].items() if t == "int"]
    df = to_whole_numbers(df, int_columns)
    df["dob"] = pd.to_datetime(df["dob"]).dt.date      # keep the date, drop the time
    return df[list(config.SCHEMAS["tennis_stats"])]


def transform_all(paths: dict) -> dict:
    """Clean every source. Returns {table_name: DataFrame}."""
    tables = {
        "forbes_athletes": transform_forbes(paths["forbes"]),
        "athlete_earnings": transform_earnings(paths["earnings"]),
        "tennis_stats": transform_tennis(paths["tennis"]),
    }
    for name, df in tables.items():
        log.info("Cleaned %s: %d rows, %d columns", name, len(df), len(df.columns))
    return tables
