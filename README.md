# Athlete Earnings Data Pipeline

A small ETL pipeline that downloads athlete earnings and tennis data, cleans it,
runs data quality checks, and loads it into a database (a local practice database or Supabase).

## Key findings
- **Tennis players earn about 78% of their income from endorsements.** NBA and soccer
  players earn most of their money from salary; for tennis players, prize money
  is only about a fifth of their income.
- **Top female tennis earners made about 44% less than men** (about $19M vs $34M per year
  on average). The prize money gap is small; most of the gap comes from endorsements.
- **Data quality:** 21 checks run before every load (latest run: 18 passed, 3 warnings,
  0 errors, 872 rows loaded). 3 issues were fixed (a misspelled name, 17 F1 drivers
  labeled NASCAR, a year stored as text) and 3 were flagged (missing year 2001,
  60 rows with no prize money split, and two different players named "Li Na").

**My rule:** fix only when I know the correct value. Otherwise flag it and
document it. Never guess or make up values.

*Findings use complete rows only (2011–2013 have no prize money / endorsements split).*

```
EXTRACT  ->  TRANSFORM  ->  CHECK  ->  LOAD
download     clean & fix    PASS/FAIL  SQLite (local) or Supabase (PostgreSQL)
```

## Data sources
| Table | Source | What it is |
|---|---|---|
| `forbes_athletes` | Forbes via Kaggle | Top 10 highest-paid athletes per year, 1990–2020 |
| `athlete_earnings` | Forbes via Kaggle | Top 10 earners in tennis, NBA, soccer, 2011–2021, split into prize money and endorsements |
| `tennis_stats` | Built from Jeff Sackmann's ATP/WTA GitHub data | Player info, best yearly ranking, match stats, 2012–2021 |

All three files are downloaded from github.com/antonbcristina/SAS-Tennis-Asset.

## Project files
| File | Job |
|---|---|
| `config.py` | All settings: source URLs, known fixes, table schemas, check thresholds |
| `extract.py` | Downloads files, with **retries** and a fallback to the last good copy |
| `transform.py` | Cleans data: column names, extra spaces, typo fixes, wrong sport labels, data types |
| `checks.py` | **Data quality checks**: ERROR stops the pipeline, WARNING is logged |
| `load.py` | Loads tables in **one transaction** (all or nothing) and records each run |
| `run_pipeline.py` | Runs everything with one command, with **logging** |
| `tests/test_pipeline.py` | 13 automated tests for the cleaning, checking and loading code |
| `exploration/check_datasets.py` | First look at the raw data, where the issues were found |
| `exploration/fix_datasets.py` | First version of the fixes, with before-and-after checks |
| `data/raw/` | Copies of the three source files, so `--skip-download` works offline |

To run the exploration scripts: `cd data/raw` then `python ../../exploration/check_datasets.py`.

## Setup (once)
```bash
pip install -r requirements.txt
```

## Run it
```bash
python run_pipeline.py                  # download, clean, check, load into the local database
python run_pipeline.py --skip-download  # use the files already in data/raw/
python run_pipeline.py --env supabase   # load into Supabase instead
python -m pytest -v                     # run the tests
```

The full history of messages is saved in `logs/pipeline.log`.
Every run (success or failure) is recorded in the `pipeline_runs` table.

## Loading into Supabase
1. In Supabase, click **Connect** (top of the dashboard) and copy the **Session pooler** connection string.
2. Copy `.env.example` to a new file named `.env`.
3. Paste the connection string into `.env` and replace `[YOUR-PASSWORD]` with your database password.
4. Run `python run_pipeline.py --env supabase`.

`.env` holds your password. Never share it or upload it to GitHub (`.gitignore` already excludes it).

## Data quality checks
**ERROR (stops the pipeline, nothing loaded):** missing columns, too few rows, negative or zero earnings,
ranks outside 1–10, years out of range, the same athlete twice in one year,
total earnings not equal to prize money + endorsements, win % outside 0–1, unknown gender values.

**WARNING (logged, loading continues):** missing years, too much missing prize money,
rows with no year, tennis rows that don't join, and names that look like misspellings.

## Known data issues (found and handled)
| Issue | How it's handled |
|---|---|
| "Grigor Dmitrov" misspelled in the earnings file | Fixed in `transform.py` (`NAME_CORRECTIONS` in config) |
| 17 rows of F1 drivers labeled "NASCAR" | Relabeled to "F1 Racing" |
| 2001 missing from the Forbes data | WARNING |
| 60 rows (2011–2013) have no prize money / endorsements split | WARNING; left empty, not set to 0 |
| "Li Na" in the tennis data is a different player (born 1994), with no ranking years | WARNING; earnings rows for Li Na don't join |
| Tennis stats start in 2012, earnings start in 2011 | 2011 tennis rows don't join (expected) |
| `previous_year_rank` contains text like ">10", "none", "?" | Kept as text |

## Ideas for next steps
- Schedule it to run automatically (GitHub Actions, or AWS Lambda + EventBridge).
- Send an alert (email/Slack) when a run fails.
- Match players on IDs instead of names.
