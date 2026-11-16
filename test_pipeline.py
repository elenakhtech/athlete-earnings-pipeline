"""
Tests: small, fake tables that prove each piece works.

Run from the athlete_pipeline folder:
    python -m pytest -v
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import checks      # noqa: E402
import load        # noqa: E402
import transform   # noqa: E402


# ------------------------------------------------------------------
# TRANSFORM tests
# ------------------------------------------------------------------
def test_column_names_are_standardized():
    df = pd.DataFrame({"Total Earnings ": [1], "Player": ["A"]})
    assert list(transform.standardize_columns(df).columns) == ["total_earnings", "player"]


def test_extra_spaces_are_removed():
    df = pd.DataFrame({"player": ["  Roger Federer "]})
    assert transform.trim_text(df)["player"][0] == "Roger Federer"


def test_misspelled_name_is_fixed():
    df = pd.DataFrame({"player": ["Grigor Dmitrov", "Rafael Nadal"]})
    fixed = transform.fix_names(df, "player")
    assert list(fixed["player"]) == ["Grigor Dimitrov", "Rafael Nadal"]


def test_f1_drivers_are_relabeled_but_nascar_drivers_are_not():
    df = pd.DataFrame({"name": ["Ayrton Senna", "Dale Earnhardt"], "sport": ["NASCAR", "NASCAR"]})
    fixed = transform.fix_f1_labels(df)
    assert list(fixed["sport"]) == ["F1 Racing", "NASCAR"]


def test_whole_numbers_keep_empty_values():
    df = pd.DataFrame({"rank": ["3", None, "x"]})
    result = transform.to_whole_numbers(df, ["rank"])["rank"]
    assert result[0] == 3 and pd.isna(result[1]) and pd.isna(result[2])


# ------------------------------------------------------------------
# CHECK tests
# ------------------------------------------------------------------
def make_earnings(**changes):
    df = pd.DataFrame({
        "player": ["A", "B"], "nationality": ["X", "Y"], "sport": ["Tennis", "NBA"],
        "team": [None, "Lakers"], "team_sport": ["No", "Yes"], "year": [2020, 2020],
        "earnings_rank": [1, 2], "total_earnings": [10.0, 20.0],
        "prize_money": [4.0, 15.0], "endorsements": [6.0, 5.0],
    })
    for col, values in changes.items():
        df[col] = values
    return df


def failed_names(results):
    return [r.name for r in results if not r.passed]


def test_good_earnings_pass_money_checks():
    results = checks.check_earnings(make_earnings())
    assert "athlete_earnings: total = prize money + endorsements" not in failed_names(results)
    assert "athlete_earnings: no negative money" not in failed_names(results)


def test_totals_that_dont_add_up_are_caught():
    results = checks.check_earnings(make_earnings(total_earnings=[99.0, 20.0]))
    assert "athlete_earnings: total = prize money + endorsements" in failed_names(results)


def test_negative_money_is_caught():
    results = checks.check_earnings(make_earnings(prize_money=[-1.0, 15.0], total_earnings=[5.0, 20.0]))
    assert "athlete_earnings: no negative money" in failed_names(results)


def test_duplicate_player_year_is_caught():
    results = checks.check_earnings(make_earnings(player=["A", "A"]))
    assert "athlete_earnings: no player twice in one year" in failed_names(results)


def test_join_check_suggests_likely_typo():
    earnings = make_earnings(player=["Grigor Dmitrov", "B"])
    tennis = pd.DataFrame({"player": ["Grigor Dimitrov"], "year": [2020]})
    results = checks.check_join(earnings, tennis)
    typo_check = [r for r in results if r.name == "join: no likely misspellings"][0]
    assert not typo_check.passed
    assert "Grigor Dimitrov" in typo_check.detail


def test_only_errors_block_loading():
    results = [checks.check("a", False, "WARNING"), checks.check("b", True, "ERROR")]
    assert checks.errors(results) == []
    assert len(checks.warnings(results)) == 1


# ------------------------------------------------------------------
# LOAD tests
# ------------------------------------------------------------------
def test_empty_values_become_null():
    assert load.python_value(float("nan"), "sqlite") is None
    assert load.python_value(pd.NA, "postgres") is None


def test_create_table_has_primary_key():
    sql = load.create_table_sql("athlete_earnings", "postgres")
    assert "PRIMARY KEY" in sql and "total_earnings double precision" in sql
