import pandas as pd
import os

INPUT = "data_cleaned/SriLanka_EventCalendar.csv"
OUTPUT = "data_cleaned/SriLanka_EventCalendar_CLEANED.csv"

df = pd.read_csv(
    INPUT,
    sep="\t",                # ← IMPORTANT
    engine="python",
    quotechar='"',
    skip_blank_lines=True
)

# Normalize column names
df.columns = [c.strip().title().replace(" ", "_") for c in df.columns]

# Clean Locations column
df["Locations"] = df["Locations"].astype(str).str.replace('"', '').str.strip()

# Strip whitespace on all string fields
for col in df.columns:
    if df[col].dtype == object:
        df[col] = df[col].str.strip()

df.to_csv(OUTPUT, index=False)

print("✅ CLEANED FILE SAVED:", OUTPUT)
print(df.head())
