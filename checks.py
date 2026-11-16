"""
CHECKS: data quality tests that run BEFORE loading.

Two levels:
  ERROR   -> something is definitely wrong. The pipeline stops and nothing is loaded.
  WARNING -> something looks unusual. It's logged, but loading continues.
"""
import difflib
import logging
from dataclasses import dataclass

import pandas as pd

import config

log = logging.getLogger("pipeline.checks")


@dataclass
class CheckResult:
    name: str
    passed: bool
    level: str          # "ERROR" or "WARNING"
    detail: str = ""


def check(name, passed, level="ERROR", detail=""):
    return CheckResult(name, bool(passed), level, detail)


# ------------------------------------------------------------------
# Checks for one table
# ------------------------------------------------------------------
def check_table_basics(name: str, df: pd.DataFrame) -> list:
    expected_columns = list(config.SCHEMAS[name])
    missing_columns = [c for c in expected_columns if c not in df.columns]
    return [
        check(f"{name}: has all expected columns", not missing_columns,
              detail=f"missing: {missing_columns}" if missing_columns else ""),
        check(f"{name}: at least {config.MIN_ROWS[name]} rows", len(df) >= config.MIN_ROWS[name],
              detail=f"{len(df)} rows"),
    ]


def check_forbes(df: pd.DataFrame) -> list:
    years_present = set(df["year"].dropna())
    missing_years = sorted(set(range(1990, 2021)) - years_present)
    return check_table_basics("forbes_athletes", df) + [
        check("forbes_athletes: earnings are positive", (df["earnings"] > 0).all()),
        check("forbes_athletes: ranks between 1 and 10", df["current_rank"].between(1, 10).all()),
        check("forbes_athletes: years between 1990 and 2020", df["year"].between(1990, 2020).all()),
        check("forbes_athletes: no athlete twice in one year",
              not df.duplicated(["name", "year"]).any()),
        check("forbes_athletes: every year present", not missing_years, level="WARNING",
              detail=f"missing years: {missing_years}" if missing_years else ""),
    ]


def check_earnings(df: pd.DataFrame) -> list:
    complete = df.dropna(subset=["prize_money", "endorsements"])
    adds_up = (complete["total_earnings"] - complete["prize_money"] - complete["endorsements"]).abs() < 0.05
    missing_share = df["prize_money"].isna().mean()
    return check_table_basics("athlete_earnings", df) + [
        check("athlete_earnings: no negative money",
              (df[["total_earnings", "prize_money", "endorsements"]].fillna(0) >= 0).all().all()),
        check("athlete_earnings: total = prize money + endorsements", adds_up.all(),
              detail=f"{(~adds_up).sum()} rows don't add up"),
        check("athlete_earnings: no player twice in one year",
              not df.duplicated(["player", "year"]).any()),
        check("athlete_earnings: little missing prize money",
              missing_share <= config.MAX_MISSING_PRIZE_SHARE, level="WARNING",
              detail=f"{missing_share:.0%} of rows have no prize money"),
    ]


def check_tennis(df: pd.DataFrame) -> list:
    has_year = df.dropna(subset=["year"])
    no_year = df[df["year"].isna()]["player"].tolist()
    return check_table_basics("tennis_stats", df) + [
        check("tennis_stats: no player twice in one year",
              not has_year.duplicated(["player_id", "year"]).any()),
        check("tennis_stats: win % between 0 and 1", df["win_per"].dropna().between(0, 1).all()),
        check("tennis_stats: gender is M or F", df["gender"].isin(["M", "F"]).all()),
        check("tennis_stats: every row has a year", not no_year, level="WARNING",
              detail=f"no year for: {no_year}" if no_year else ""),
    ]


# ------------------------------------------------------------------
# Checks across tables
# ------------------------------------------------------------------
def check_join(earnings: pd.DataFrame, tennis: pd.DataFrame) -> list:
    tennis_earnings = earnings[earnings["sport"] == "Tennis"]
    joined = tennis_earnings.merge(tennis[["player", "year"]], on=["player", "year"],
                                   how="left", indicator=True)
    unmatched = joined[joined["_merge"] == "left_only"]
    match_rate = 1 - len(unmatched) / len(tennis_earnings)

    # Suggest likely misspellings for names that never match
    known_names = set(tennis["player"])
    suggestions = {}
    for name in set(unmatched["player"]) - known_names:
        close = difflib.get_close_matches(name, known_names, n=1, cutoff=0.8)
        if close:
            suggestions[name] = close[0]

    results = [
        check("join: tennis earnings match tennis stats",
              match_rate >= config.MIN_JOIN_MATCH_RATE, level="WARNING",
              detail=f"{match_rate:.0%} matched; unmatched: "
                     + ", ".join(f"{p} {y}" for p, y in zip(unmatched["player"], unmatched["year"]))),
        check("join: no likely misspellings", not suggestions, level="WARNING",
              detail=f"possible typos (add to NAME_CORRECTIONS): {suggestions}" if suggestions else ""),
    ]
    return results


# ------------------------------------------------------------------
# Run everything
# ------------------------------------------------------------------
def run_all_checks(tables: dict) -> list:
    results = (
        check_forbes(tables["forbes_athletes"])
        + check_earnings(tables["athlete_earnings"])
        + check_tennis(tables["tennis_stats"])
        + check_join(tables["athlete_earnings"], tables["tennis_stats"])
    )
    for r in results:
        status = "PASS" if r.passed else ("FAIL" if r.level == "ERROR" else "WARN")
        line = f"[{status}] {r.name}" + (f"  ({r.detail})" if r.detail and not r.passed else "")
        (log.info if r.passed else log.warning if r.level == "WARNING" else log.error)(line)
    return results


def errors(results: list) -> list:
    return [r for r in results if not r.passed and r.level == "ERROR"]


def warnings(results: list) -> list:
    return [r for r in results if not r.passed and r.level == "WARNING"]
