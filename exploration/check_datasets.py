import os
import pandas as pd
 
# Show all columns when printing tables
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
 
 
def title(text):
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)
 
 
def first_look(df, name):
    """The 5 checks to run on ANY new dataset."""
    title(f"FIRST LOOK: {name}")
 
    print(f"\n1. SIZE: {df.shape[0]} rows, {df.shape[1]} columns")
 
    print("\n2. FIRST 3 ROWS:")
    print(df.head(3))
 
    print("\n3. COLUMN TYPES (int = whole number, float = decimal, str/object = text):")
    print(df.dtypes)
 
    print("\n4. EMPTY CELLS PER COLUMN:")
    empty = df.isna().sum()
    print(empty[empty > 0] if empty.sum() > 0 else "   None")
 
    print("\n5. NUMBER SUMMARY (look at min and max - do they make sense?):")
    print(df.describe().round(1))
 
 
# ----------------------------------------------------------------------
# LOAD THE 3 FILES
# ----------------------------------------------------------------------
files = ["Forbes_Richest_Athletes_1990-2020.csv", "Athletes_Earnings.xlsx", "demo_rank_matches.sas7bdat"]
for f in files:
    if not os.path.exists(f):
        print(f"Can't find '{f}'. Make sure it's in the same folder as this script.")
        raise SystemExit
 
forbes = pd.read_csv("Forbes_Richest_Athletes_1990-2020.csv")
earnings = pd.read_excel("Athletes_Earnings.xlsx")
tennis = pd.read_sas("demo_rank_matches.sas7bdat", encoding="latin1")
print("All 3 files loaded!")
 
 
# ======================================================================
# DATASET 1: FORBES
# ======================================================================
first_look(forbes, "Forbes Richest Athletes 1990-2020")
 
title("MORE CHECKS: Forbes")
 
# Rows per year (expect 10)
rows_per_year = forbes.groupby("Year").size()
print("\n6. YEARS THAT DON'T HAVE EXACTLY 10 ATHLETES:")
print(rows_per_year[rows_per_year != 10])
 
missing_years = sorted(set(range(1990, 2021)) - set(forbes["Year"]))
print("\n7. YEARS MISSING COMPLETELY:", missing_years if missing_years else "None")
 
# Duplicates: same athlete twice in the same year
dupes = forbes[forbes.duplicated(["Name", "Year"], keep=False)]
print("\n8. SAME ATHLETE TWICE IN ONE YEAR:", len(dupes), "rows")
 
# Ties: same rank twice in the same year
ties = forbes[forbes.duplicated(["Year", "Current_Rank"], keep=False)]
print("\n9. TIED RANKS (same year, same rank):")
print(ties[["Year", "Current_Rank", "Name", "Earnings"]].to_string(index=False))
 
# Text values
print("\n10. ALL SPORTS (look for strange or wrong labels):")
print(sorted(forbes["Sport"].unique()))
 
print("\n11. NASCAR DRIVERS (are they all really NASCAR?):")
print(sorted(forbes[forbes["Sport"] == "NASCAR"]["Name"].unique()))
 
# Numbers stored as text
ranks = forbes["Previous_Year_Rank"].dropna()
not_numbers = ranks[pd.to_numeric(ranks, errors="coerce").isna()]
print("\n12. Previous_Year_Rank VALUES THAT AREN'T NUMBERS:")
print(sorted(not_numbers.unique()))
 
# Extreme values
print("\n13. HIGHEST AND LOWEST EARNINGS (are they real?):")
print(forbes.nlargest(2, "Earnings")[["Name", "Year", "Sport", "Earnings"]].to_string(index=False))
print(forbes.nsmallest(2, "Earnings")[["Name", "Year", "Sport", "Earnings"]].to_string(index=False))
 
 
# ======================================================================
# DATASET 2: EARNINGS
# ======================================================================
first_look(earnings, "Athletes Earnings (Tennis, NBA, Soccer)")
 
title("MORE CHECKS: Earnings")
 
print("\n6. ROWS PER SPORT:")
print(earnings["Sport"].value_counts())
 
missing_prize = earnings[earnings["Prize_Money"].isna()]
print(f"\n7. ROWS WITH NO PRIZE MONEY: {len(missing_prize)}  - by sport and year:")
print(missing_prize.groupby(["Sport", "Year"]).size())
 
dupes = earnings[earnings.duplicated(["Player", "Year"], keep=False)]
print("\n8. SAME PLAYER TWICE IN ONE YEAR:", len(dupes), "rows")
 
complete = earnings.dropna(subset=["Prize_Money", "Endorsements"])
difference = (complete["Total_Earnings"] - complete["Prize_Money"] - complete["Endorsements"]).abs()
print("\n9. ROWS WHERE TOTAL != PRIZE + ENDORSEMENTS:", (difference >= 0.05).sum())
 
negative = (earnings[["Total_Earnings", "Prize_Money", "Endorsements"]] < 0).sum().sum()
print("\n10. NEGATIVE MONEY VALUES:", negative)
 
 
# ======================================================================
# DATASET 3: TENNIS STATS
# ======================================================================
first_look(tennis, "Tennis Demographics, Rankings and Matches")
 
title("MORE CHECKS: Tennis")
 
print("\n6. PLAYERS BY GENDER:")
print(tennis.drop_duplicates("Player")["Gender"].value_counts())
 
no_year = tennis[tennis["Year"].isna()]
print("\n7. ROWS WITH NO YEAR:")
print(no_year[["Player", "DOB", "Gender", "Year", "Rank"]].to_string(index=False) if len(no_year) else "   None")
 
print("\n8. WIN % OUTSIDE 0-1:", (~tennis["Win_Per"].dropna().between(0, 1)).sum())
 
 
# ======================================================================
# CHECK ACROSS DATASETS: DO EARNINGS AND TENNIS STATS JOIN?
# ======================================================================
title("JOIN CHECK: tennis earnings + tennis stats (on Player and Year)")
 
tennis["Year"] = pd.to_numeric(tennis["Year"]).astype("Int64")
tennis_earnings = earnings[earnings["Sport"] == "Tennis"]
 
joined = tennis_earnings.merge(tennis[["Player", "Year"]], on=["Player", "Year"],
                               how="left", indicator=True)
unmatched = joined[joined["_merge"] == "left_only"]
 
print(f"\nMatched: {len(joined) - len(unmatched)} of {len(joined)} tennis rows")
print("Rows that did NOT match:")
print(unmatched[["Player", "Year"]].to_string(index=False))
 
# Names in earnings that never appear in tennis stats - possible typos?
never_found = sorted(set(unmatched["Player"]) - set(tennis["Player"]))
print("\nNames that don't exist in tennis stats at all (typo or missing player?):")
print(never_found)
 
 
title("DONE - read the results above and write down every problem you found")

