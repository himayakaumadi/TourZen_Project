# scripts/create_national_totals.py
import os
import pandas as pd
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "..", "data_cleaned")
inp = os.path.join(BASE, "monthly_tourism_cleaned.csv")
out = os.path.join(BASE, "national_monthly_arrivals.csv")

if not os.path.exists(inp):
    print("Input file not found:", inp)
    raise SystemExit(1)

df = pd.read_csv(inp, dtype=str)

# Standardize and clean
df.columns = df.columns.str.upper().str.strip()
required = {"YEAR", "MONTH", "ARRIVALS"}
if not required.issubset(set(df.columns)):
    print("Input missing required columns. Found:", df.columns.tolist())
    raise SystemExit(1)

# Clean arrivals: convert 'nan' etc to numeric
df["ARRIVALS"] = pd.to_numeric(df["ARRIVALS"], errors="coerce").fillna(0)

# Standardize MONTH and YEAR
df["MONTH"] = df["MONTH"].astype(str).str.upper()
df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce").astype(int)

# Group by YEAR+MONTH to get national totals
national = df.groupby(["YEAR", "MONTH"], as_index=False)["ARRIVALS"].sum()
national = national.rename(columns={"ARRIVALS": "TOTAL_ARRIVALS"})

# Save
national.to_csv(out, index=False)
print("✅ national_monthly_arrivals.csv written to:", out)
print(national.head(12).to_string(index=False))
