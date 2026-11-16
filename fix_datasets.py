
import pandas as pd

forbes = pd.read_csv("Forbes_Richest_Athletes_1990-2020.csv")
earnings = pd.read_excel("Athletes_Earnings.xlsx")
tennis = pd.read_sas("demo_rank_matches.sas7bdat", encoding="latin1")


# ======================================================================
# FIX 1: Misspelled name "Grigor Dmitrov" -> "Grigor Dimitrov"
# ======================================================================
print("FIX 1: Misspelled name")
print("  Before:", earnings[earnings["Player"].str.startswith("Grigor")]["Player"].unique().tolist())

earnings["Player"] = earnings["Player"].replace("Grigor Dmitrov", "Grigor Dimitrov")

print("  After: ", earnings[earnings["Player"].str.startswith("Grigor")]["Player"].unique().tolist())


# ======================================================================
# FIX 2: F1 drivers labeled "NASCAR" -> "F1 Racing"
# ======================================================================
print("\nFIX 2: F1 drivers labeled NASCAR")
f1_drivers = ["Ayrton Senna", "Michael Schumacher", "Alain Prost", "Nigel Mansell",
              "Gerhard Berger", "Jacques Villeneuve", "Lewis Hamilton"]

wrong = forbes["Name"].isin(f1_drivers) & (forbes["Sport"] == "NASCAR")
print("  Before: rows wrongly labeled NASCAR =", wrong.sum())

forbes.loc[wrong, "Sport"] = "F1 Racing"

still_wrong = forbes["Name"].isin(f1_drivers) & (forbes["Sport"] == "NASCAR")
print("  After:  rows wrongly labeled NASCAR =", still_wrong.sum())
print("  NASCAR drivers now:", sorted(forbes[forbes["Sport"] == "NASCAR"]["Name"].unique()))


# ======================================================================
# FIX 3: Tennis "Year" stored as text -> whole number
# ======================================================================
print("\nFIX 3: Year stored as text")
print("  Before: tennis Year type =", tennis["Year"].dtype, "| earnings Year type =", earnings["Year"].dtype)

tennis["Year"] = pd.to_numeric(tennis["Year"]).astype("Int64")   # Int64 = whole number that can be empty

print("  After:  tennis Year type =", tennis["Year"].dtype, "| earnings Year type =", earnings["Year"].dtype)


# ======================================================================
# CHECK: does the join work better now?
# ======================================================================
print("\nCHECK: tennis earnings joined to tennis stats")
tennis_earnings = earnings[earnings["Sport"] == "Tennis"]
joined = tennis_earnings.merge(tennis[["Player", "Year"]], on=["Player", "Year"],
                               how="left", indicator=True)
matched = (joined["_merge"] == "both").sum()
print(f"  Matched: {matched} of {len(joined)}   (was 96 before the fixes)")


# ======================================================================
# SAVE clean copies (new files - the originals stay untouched)
# ======================================================================
forbes.to_csv("Forbes_CLEAN.csv", index=False)
earnings.to_csv("Earnings_CLEAN.csv", index=False)
tennis.to_csv("Tennis_CLEAN.csv", index=False)
print("\nSaved: Forbes_CLEAN.csv, Earnings_CLEAN.csv, Tennis_CLEAN.csv")