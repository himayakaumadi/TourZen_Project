#!/usr/bin/env python3
"""
Clean trends-related raw datasets and save cleaned CSVs to data_cleaned/.
Usage:
    python scripts/clean_trends_data.py
"""

import os
import glob
import pandas as pd
from pathlib import Path

# ---------- EDIT PATHS HERE if needed ----------
BASE = Path(r"C:\Users\DELL\Downloads\University\DataManagementProject\tourzen_app")
RAW = BASE / "data_raw"
CLEAN = BASE / "data_cleaned"
CLEAN.mkdir(parents=True, exist_ok=True)

# Input files (existing in your project)
TRAINING_REGION = RAW / "training_dataset.csv"   # you already referenced
AGE_XLSX = RAW / "TouristArrivalByAge.xlsx"
NATIONAL_MONTHLY = CLEAN / "national_monthly_arrivals_fixed.csv"  # you said this already exists cleaned; we'll still read & re-clean/sanitize
# Income files pattern
INCOME_PATTERN = str(RAW / "Tourism_Income_*.csv")


# Utility helpers
def clean_numeric_series(s):
    """Remove commas and convert to numeric (float)."""
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def normalize_month_name(m):
    if pd.isna(m):
        return m
    m = str(m).strip()
    # Try to handle numeric months (1, 01) or full/short names
    month_map = {
        'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
        'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
        'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
    }
    # numeric?
    try:
        n = int(m)
        import calendar
        return calendar.month_name[n]
    except Exception:
        pass
    low = m.lower()
    for key in month_map:
        if low.startswith(key):
            return month_map[key]
    return m.title()  # fallback


print("Starting cleaning...")

# ---------- 1) Clean Region training_dataset.csv ----------
if TRAINING_REGION.exists():
    print(f"Loading region file: {TRAINING_REGION}")
    df_reg = pd.read_csv(TRAINING_REGION)
    # Standardize column names
    df_reg.columns = df_reg.columns.str.strip()

    # Ensure YEAR column
    if 'YEAR' not in df_reg.columns and 'Year' in df_reg.columns:
        df_reg.rename(columns={'Year': 'YEAR'}, inplace=True)

    # Clean ARRIVALS
    if 'ARRIVALS' in df_reg.columns:
        df_reg['ARRIVALS'] = clean_numeric_series(df_reg['ARRIVALS']).fillna(0).astype(int)
    else:
        # try lowercase variants
        for c in df_reg.columns:
            if 'arrival' in c.lower() or 'arriv' in c.lower():
                df_reg.rename(columns={c: 'ARRIVALS'}, inplace=True)
                df_reg['ARRIVALS'] = clean_numeric_series(df_reg['ARRIVALS']).fillna(0).astype(int)
                break

    # Ensure MONTH & MONTH_NUM columns present or derive
    if 'MONTH' in df_reg.columns:
        df_reg['MONTH'] = df_reg['MONTH'].astype(str).str.strip()
        df_reg['MONTH_NAME'] = df_reg['MONTH'].apply(normalize_month_name)
    elif 'MONTH_NUM' in df_reg.columns:
        import calendar
        df_reg['MONTH_NAME'] = df_reg['MONTH_NUM'].astype(int).apply(lambda x: calendar.month_name[x])
    else:
        df_reg['MONTH_NAME'] = pd.NA

    # DATE parse if present
    if 'DATE' in df_reg.columns:
        df_reg['DATE'] = pd.to_datetime(df_reg['DATE'], errors='coerce')

    # REGION and COUNTRY clean
    for cname in ['REGION', 'COUNTRY']:
        if cname in df_reg.columns:
            df_reg[cname] = df_reg[cname].astype(str).str.strip()

    # Save cleaned file
    out_region = CLEAN / "training_dataset_region_cleaned.csv"
    df_reg.to_csv(out_region, index=False)
    print(f"Saved cleaned region dataset -> {out_region}")
    print(df_reg.head(3).to_string(index=False))
else:
    print(f"Warning: region training file not found at {TRAINING_REGION}")

# ---------- 2) Clean TouristArrivalByAge.xlsx ----------
if AGE_XLSX.exists():
    print(f"\nLoading age file: {AGE_XLSX}")
    df_age = pd.read_excel(AGE_XLSX)
    df_age.columns = df_age.columns.str.strip()

    # Find Year column
    year_cols = [c for c in df_age.columns if 'year' in c.lower()]
    if year_cols:
        df_age.rename(columns={year_cols[0]: 'Year'}, inplace=True)

    # Find count column
    count_cols = [c for c in df_age.columns if ('no' in c.lower() and 'tourist' in c.lower()) or ('number' in c.lower() and 'tourist' in c.lower())]
    if not count_cols:
        # fallback try to identify numeric-like second column
        numeric_candidates = [c for c in df_age.columns if df_age[c].dtype == 'object' or df_age[c].dtype.kind in 'iuif']
        if len(numeric_candidates) >= 1:
            count_cols = [numeric_candidates[-1]]
    if count_cols:
        cnt = count_cols[0]
        df_age[cnt] = clean_numeric_series(df_age[cnt]).astype('Int64')
        df_age.rename(columns={cnt: 'No Of Tourist'}, inplace=True)
    else:
        df_age['No Of Tourist'] = pd.NA

    # Age column cleanup
    age_cols = [c for c in df_age.columns if 'age' in c.lower()]
    if age_cols:
        df_age.rename(columns={age_cols[0]: 'Age'}, inplace=True)
    else:
        # assume second column is Age
        if df_age.shape[1] >= 2:
            df_age.rename(columns={df_age.columns[1]: 'Age'}, inplace=True)

    df_age['Age'] = df_age['Age'].astype(str).str.strip()
    # Ensure Year numeric
    if 'Year' in df_age.columns:
        df_age['Year'] = pd.to_numeric(df_age['Year'], errors='coerce').astype('Int64')

    # Drop rows where Year or Age missing
    df_age = df_age.dropna(subset=['Year', 'Age'])

    out_age = CLEAN / "tourist_arrivals_by_age_cleaned.csv"
    df_age.to_csv(out_age, index=False)
    print(f"Saved cleaned age dataset -> {out_age}")
    print(df_age.head(6).to_string(index=False))
else:
    print(f"Warning: age file not found at {AGE_XLSX}")

# ---------- 3) Clean national monthly arrivals (if exists) ----------
if NATIONAL_MONTHLY.exists():
    print(f"\nLoading monthly arrivals file: {NATIONAL_MONTHLY}")
    df_mon = pd.read_csv(NATIONAL_MONTHLY)
    df_mon.columns = df_mon.columns.str.strip()

    # Normalize column names to YEAR, MONTH, TOTAL_ARRIVALS, COVID maybe
    col_map = {}
    for c in df_mon.columns:
        lc = c.lower()
        if 'year' in lc:
            col_map[c] = 'YEAR'
        elif 'month' in lc:
            col_map[c] = 'MONTH'
        elif 'total' in lc and ('arrival' in lc or 'arriv' in lc or 'total' in lc):
            col_map[c] = 'TOTAL_ARRIVALS'
        elif 'covid' in lc:
            col_map[c] = 'COVID'
    df_mon = df_mon.rename(columns=col_map)

    # Clean totals
    if 'TOTAL_ARRIVALS' in df_mon.columns:
        df_mon['TOTAL_ARRIVALS'] = clean_numeric_series(df_mon['TOTAL_ARRIVALS']).fillna(0).astype(int)
    # normalize month names
    if 'MONTH' in df_mon.columns:
        df_mon['MONTH'] = df_mon['MONTH'].apply(normalize_month_name)

    out_month = CLEAN / "national_monthly_arrivals_fixed_cleaned.csv"
    df_mon.to_csv(out_month, index=False)
    print(f"Saved cleaned monthly arrivals -> {out_month}")
    print(df_mon.head(6).to_string(index=False))
else:
    print(f"Warning: monthly arrivals file not found at {NATIONAL_MONTHLY}")

# ---------- 4) Combine & clean Income CSVs ----------
income_files = sorted(glob.glob(INCOME_PATTERN))
if income_files:
    print("\nFound income files:")
    for f in income_files:
        print(" ", f)

    income_frames = []
    for f in income_files:
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip()

        # normalize column names to expected
        col_map = {}
        for c in df.columns:
            lc = c.lower()
            if lc.startswith('month'):
                col_map[c] = 'Month'
            elif 'number' in lc and 'tourist' in lc:
                col_map[c] = 'Number of tourist arrivals'
            elif ('average' in lc and 'value' in lc) or 'avg value' in lc:
                col_map[c] = 'Average value of the Month'
            elif ('average' in lc and 'duration' in lc) or 'avg duration' in lc:
                col_map[c] = 'Average duration of the Month'
            elif 'total' in lc and ('usd' in lc or 'mn' in lc or 'value' in lc):
                col_map[c] = 'Total value (USD Mn)'
        df = df.rename(columns=col_map)

        # ensure expected cols exist
        for needed in ['Month', 'Number of tourist arrivals', 'Average value of the Month', 'Average duration of the Month', 'Total value (USD Mn)']:
            if needed not in df.columns:
                df[needed] = pd.NA

        # clean numeric columns
        df['Number of tourist arrivals'] = clean_numeric_series(df['Number of tourist arrivals']).astype('Int64')
        df['Average value of the Month'] = pd.to_numeric(df['Average value of the Month'], errors='coerce')
        df['Average duration of the Month'] = pd.to_numeric(df['Average duration of the Month'], errors='coerce')
        df['Total value (USD Mn)'] = clean_numeric_series(df['Total value (USD Mn)'])

        # normalize month name
        df['Month'] = df['Month'].apply(normalize_month_name)

        # infer year from filename (last 4 digits) fallback to NaN
        fname = os.path.basename(f)
        year = None
        import re
        m = re.search(r'(\d{4})', fname)
        if m:
            year = int(m.group(1))
        df['Year'] = year

        income_frames.append(df[['Year', 'Month', 'Number of tourist arrivals', 'Average value of the Month', 'Average duration of the Month', 'Total value (USD Mn)']])

    df_income = pd.concat(income_frames, ignore_index=True)
    # Sort by Year then month order
    month_order = ['January','February','March','April','May','June','July','August','September','October','November','December']
    df_income['MonthOrder'] = df_income['Month'].apply(lambda m: month_order.index(m) if m in month_order else 999)
    df_income = df_income.sort_values(['Year', 'MonthOrder']).drop(columns=['MonthOrder'])

    out_income = CLEAN / "tourism_income_combined_cleaned.csv"
    df_income.to_csv(out_income, index=False)
    print(f"\nSaved combined cleaned income -> {out_income}")
    print(df_income.head(12).to_string(index=False))
else:
    print("\nNo income files found matching pattern:", INCOME_PATTERN)

print("\nCleaning process completed.")
