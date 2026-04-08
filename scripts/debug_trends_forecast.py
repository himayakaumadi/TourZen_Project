import pandas as pd
import os

BASE = "data_cleaned"
file = os.path.join(BASE, "forecast_ensemble.csv")

df = pd.read_csv(file)
print("==== FILE LOADED ====")
print(df.head())
print("\nCOLUMNS:", df.columns.tolist())

# Convert ds → month name if exists
if "ds" in df.columns:
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    print("\nMONTHS FROM ds:", df["ds"].dt.month_name().unique())
else:
    print("No 'ds' column found.")

# Show if month column exists
if "month" in df.columns:
    print("MONTH COLUMN UNIQUE:", df["month"].unique())

print("\nCHECK ensemble_pred:")
print(df["ensemble_pred"].head() if "ensemble_pred" in df.columns else "NO ensemble_pred")
