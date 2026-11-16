"""
Settings for the pipeline, kept in one place.
Change values here instead of searching through the code.
"""

# ------------------------------------------------------------------
# EXTRACT: where the raw data comes from
# ------------------------------------------------------------------
BASE_URL = "https://raw.githubusercontent.com/antonbcristina/SAS-Tennis-Asset/main/"

SOURCES = {
    "forbes":   "Forbes_Richest_Athletes_1990-2020.csv",
    "earnings": "Athletes_Earnings.xlsx",
    "tennis":   "demo_rank_matches.sas7bdat",
}

RAW_DIR = "data/raw"          # downloaded files are saved here
DOWNLOAD_RETRIES = 3          # try this many times before giving up
DOWNLOAD_TIMEOUT = 30         # seconds to wait for a response


# ------------------------------------------------------------------
# TRANSFORM: known data fixes
# ------------------------------------------------------------------
# Misspelled names -> correct spelling
NAME_CORRECTIONS = {
    "Grigor Dmitrov": "Grigor Dimitrov",
}

# Formula 1 drivers that the source data labels as "NASCAR"
F1_DRIVERS = [
    "Ayrton Senna", "Michael Schumacher", "Alain Prost", "Nigel Mansell",
    "Gerhard Berger", "Jacques Villeneuve", "Lewis Hamilton", "Kimi Raikkonen",
]


# ------------------------------------------------------------------
# LOAD: table names and column types (the "schema")
# Types: text, int, float, date
# ------------------------------------------------------------------
SCHEMAS = {
    "forbes_athletes": {
        "name": "text", "nationality": "text", "current_rank": "int",
        "previous_year_rank": "text", "sport": "text", "year": "int",
        "earnings": "float", "team_sport": "text",
    },
    "athlete_earnings": {
        "player": "text", "nationality": "text", "sport": "text", "team": "text",
        "team_sport": "text", "year": "int", "earnings_rank": "int",
        "total_earnings": "float", "prize_money": "float", "endorsements": "float",
    },
    "tennis_stats": {
        "player_id": "int", "player": "text", "dob": "date", "gender": "text",
        "hand": "text", "ioc": "text", "height": "int", "year": "int",
        "rank": "int", "points": "int", "tourneys": "int", "slams": "int",
        "matches": "int", "w": "int", "l": "int", "win_per": "float",
        "max_ace": "int", "max_df": "int", "total_ace": "int", "total_df": "int",
    },
}

LOCAL_DB = "data/athletes_local.db"   # the practice database (SQLite file)


# ------------------------------------------------------------------
# CHECKS: thresholds
# ------------------------------------------------------------------
MIN_ROWS = {"forbes_athletes": 250, "athlete_earnings": 300, "tennis_stats": 200}
MIN_JOIN_MATCH_RATE = 0.85        # at least 85% of tennis earnings rows must join
MAX_MISSING_PRIZE_SHARE = 0.10    # warn if more than 10% of prize money is empty
