import pandas as pd
import os

# Input & Output
BASE = os.path.join(os.path.dirname(__file__), "..", "data_cleaned")
IN_FILE = os.path.join(BASE, "national_monthly_arrivals.csv")
OUT_FILE = os.path.join(BASE, "national_monthly_arrivals_fixed.csv")

# Load dataset
df = pd.read_csv(IN_FILE)

# Standardize
df["MONTH"] = df["MONTH"].astype(str).str.capitalize()
df["YEAR"] = df["YEAR"].astype(int)
df["TOTAL_ARRIVALS"] = pd.to_numeric(df["TOTAL_ARRIVALS"], errors="coerce")

print("Before fixing zeros:\n", df.head(20))

# Step 1 — Convert zeros to NA
df["TOTAL_ARRIVALS"] = df["TOTAL_ARRIVALS"].replace(0, pd.NA)

# Step 2 — Forward fill (use previous real month)
df["TOTAL_ARRIVALS"] = df["TOTAL_ARRIVALS"].fillna(method="ffill")

# Step 3 — Add COVID indicator
df["COVID"] = 0
df.loc[df["YEAR"].isin([2020, 2021]), "COVID"] = 1

# Save new cleaned file
df.to_csv(OUT_FILE, index=False)

print("\nFixed dataset saved to:", OUT_FILE)
print(df.head(20))
