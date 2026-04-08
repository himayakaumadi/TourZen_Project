from flask import Blueprint, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from prophet import Prophet
import glob
import os
import io
from functools import lru_cache
from flask import session
from utils.report_generator import CorporateReport
from .prediction_logic import predict_monthly, predict_region_proportional, predict_age_proportional, predict_income

trends_bp = Blueprint('trends', __name__)

# ===============================
# LOAD DATASETS ONCE
# ===============================

# Set project root relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CLEANED = os.path.join(BASE_DIR, "data_cleaned")
DATA_RAW = os.path.join(BASE_DIR, "data_raw")

# Region dataset
df_region = pd.read_csv(os.path.join(DATA_CLEANED, "training_dataset.csv"))
# ensure YEAR numeric
if 'YEAR' in df_region.columns:
    df_region['YEAR'] = pd.to_numeric(df_region['YEAR'], errors='coerce').astype('Int64')

# Age dataset - preprocess
df_age = pd.read_excel(os.path.join(DATA_RAW, "TouristArrivalByAge.xlsx"))

# Clean column names and values
df_age.columns = df_age.columns.str.strip()
if 'Age' in df_age.columns:
    df_age['Age'] = df_age['Age'].astype(str).str.strip()
# normalize No Of Tourist column name variations
possible_count_cols = [c for c in df_age.columns if 'no' in c.lower() and 'tourist' in c.lower()]
if possible_count_cols:
    count_col = possible_count_cols[0]
else:
    count_col = 'No Of Tourist'  # fallback

df_age[count_col] = df_age[count_col].astype(str).str.replace(',', '').str.strip()
df_age[count_col] = pd.to_numeric(df_age[count_col], errors='coerce').astype('Int64')
# Ensure Year numeric
year_col = [c for c in df_age.columns if 'year' in c.lower()]
if year_col:
    df_age[year_col[0]] = pd.to_numeric(df_age[year_col[0]], errors='coerce').astype('Int64')
    df_age.rename(columns={year_col[0]: 'Year'}, inplace=True)
else:
    df_age.rename(columns={df_age.columns[0]: 'Year'}, inplace=True)  # best-effort

df_age = df_age.dropna(subset=['Year', 'Age', count_col])
df_age.rename(columns={count_col: 'No Of Tourist'}, inplace=True)
df_age['Year'] = df_age['Year'].astype(int)
df_age = df_age.sort_values(['Age', 'Year'])

# Monthly national arrivals dataset
df_month = pd.read_csv(os.path.join(DATA_CLEANED, "national_monthly_arrivals_fixed.csv"))
# normalize column names
df_month.columns = df_month.columns.str.strip().str.upper()
# Expect YEAR, MONTH, TOTAL_ARRIVALS
if 'YEAR' in df_month.columns:
    df_month.rename(columns={c: c for c in df_month.columns}, inplace=True)
# ensure TOTAL_ARRIVALS exists
if 'TOTAL_ARRIVALS' not in df_month.columns:
    # try other variants
    for c in df_month.columns:
        if 'ARRIV' in c:
            df_month.rename(columns={c: 'TOTAL_ARRIVALS'}, inplace=True)
            break

# ===============================
# LOAD & CLEAN TOURISM INCOME CSVs (2022–2025)
# ===============================
income_files = glob.glob(os.path.join(DATA_RAW, "Tourism_Income_*.csv"))

income_list = []
for file in sorted(income_files):
    df = pd.read_csv(file)
    # Extract year from filename, fallback to guessing from file contents
    fname = os.path.basename(file)
    try:
        year = int(fname.split("_")[-1].split(".")[0])
    except Exception:
        # try to infer from a column if present
        year = None

    df.columns = df.columns.str.strip()

    # Normalize columns - try common header names
    # Map variants to expected names
    col_map = {}
    for c in df.columns:
        c_low = c.lower().strip()
        if 'month' == c_low or c_low.startswith('month'):
            col_map[c] = 'Month'
        elif 'number' in c_low and 'tourist' in c_low:
            col_map[c] = 'Number of tourist arrivals'
        elif 'average value' in c_low or 'avg value' in c_low:
            col_map[c] = 'Average value of the Month'
        elif 'average duration' in c_low or 'avg duration' in c_low:
            col_map[c] = 'Average duration of the Month'
        elif 'total' in c_low and ('usd' in c_low or 'value' in c_low or 'mn' in c_low):
            col_map[c] = 'Total value (USD Mn)'

    df = df.rename(columns=col_map)

    # Ensure required columns exist
    required = ['Month', 'Number of tourist arrivals', 'Average value of the Month', 'Average duration of the Month', 'Total value (USD Mn)']
    for r in required:
        if r not in df.columns:
            # add column with NaNs if missing
            df[r] = pd.NA

    # clean numeric columns
    df['Number of tourist arrivals'] = df['Number of tourist arrivals'].astype(str).str.replace(',', '').str.strip()
    df['Number of tourist arrivals'] = pd.to_numeric(df['Number of tourist arrivals'], errors='coerce')

    df['Average value of the Month'] = pd.to_numeric(df['Average value of the Month'], errors='coerce')
    df['Average duration of the Month'] = pd.to_numeric(df['Average duration of the Month'], errors='coerce')

    df['Total value (USD Mn)'] = df['Total value (USD Mn)'].astype(str).str.replace(',', '').str.strip()
    df['Total value (USD Mn)'] = pd.to_numeric(df['Total value (USD Mn)'], errors='coerce')

    df['Month'] = df['Month'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)

    if year is None:
        # try to obtain a year column or assume by file name last 4 digits
        # fallback to 0 if can't determine (shouldn't happen with your filenames)
        import re
        m = re.search(r'(\d{4})', fname)
        year = int(m.group(1)) if m else 0

    df['Year'] = year
    income_list.append(df[required + ['Year']])

# Combine
if income_list:
    df_income = pd.concat(income_list, ignore_index=True)
else:
    # create empty df with columns if no files found
    df_income = pd.DataFrame(columns=['Month', 'Number of tourist arrivals', 'Average value of the Month', 'Average duration of the Month', 'Total value (USD Mn)', 'Year'])

# ===============================
# ROUTES
# ===============================

@trends_bp.route('/trends')
def trends():
    years = list(range(2026, 2036))
    username = session.get("user", "")  # fetch username safely
    return render_template("trends.html", years=years, username=username)


@trends_bp.route('/predict_trends', methods=['POST'])
def predict_trends():
    data = request.get_json()

    if not data or "year" not in data:
        return jsonify({"error": "Missing year"}), 400

    selected_year = int(data["year"])

    # 1. PRIMARY ENGINE: National Monthly Arrivals (Source of Truth)
    # This is the most accurate model and defines the total for the year
    month_data = predict_monthly(selected_year)
    total_annual_arrivals = sum(month_data.values())

    # 2. DERIVED DATA: Breakdowns based on Primary Engine total
    region_data = predict_region_proportional(selected_year, total_annual_arrivals)
    age_data = predict_age_proportional(selected_year, total_annual_arrivals)
    income_data = predict_income(selected_year, month_data)

    return jsonify({
        "region": region_data,
        "age": age_data,
        "month": month_data,
        "income": income_data
    })


@trends_bp.route('/download_report/<int:year>', methods=['GET', 'POST'])
def download_report(year):
    # Try to get data from POST request (from frontend)
    if request.method == 'POST':
        data = request.get_json()
    else:
        # Fallback to GET: Re-run predictions (now cached)
        month_data = predict_monthly(year)
        total_annual = sum(month_data.values())
        
        region_data = predict_region_proportional(year, total_annual)
        age_data = predict_age_proportional(year, total_annual)
        income_data = predict_income(year, month_data)

        data = {
            "region": region_data,
            "age": age_data,
            "month": month_data,
            "income": income_data
        }

    # Generate PDF in memory
    buffer = io.BytesIO()
    report = CorporateReport(year, data)
    report.build(buffer)
    buffer.seek(0)

    filename = f"TourZen_Full_Report_{year}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ===============================
# FORECAST HELPERS
# ===============================

@lru_cache(maxsize=128)
def forecast_metric_cached(metric, selected_year):
    """
    Cached version of forecast_metric using global df_income.
    """
    return forecast_metric(df_income, metric, selected_year)

def forecast_metric(df, metric, selected_year):
    """
    Forecast a single metric (monthly) using Prophet and return a dict Month->value
    """
    temp = df.copy()

    # Build ds column: Year-Month (use first day of month)
    # temp expected to have 'Year' and 'Month'
    temp['Month'] = temp['Month'].astype(str).str.strip()
    month_map = {
        "January":1,"February":2,"March":3,"April":4,"May":5,"June":6,
        "July":7,"August":8,"September":9,"October":10,"November":11,"December":12
    }

    temp['Month'] = temp['Month'].str.title()
    temp['month_num'] = temp['Month'].map(month_map)
    temp['ds'] = pd.to_datetime(temp['Year'].astype(str) + "-" + temp['month_num'].astype(str) + "-01")
    # y needs to be numeric and stabilized with log transformation
    # Log transformation prevents negative predictions and stabilizes variance
    temp['y_raw'] = pd.to_numeric(temp[metric], errors='coerce')
    temp = temp.dropna(subset=['ds', 'y_raw'])
    
    if temp.empty:
        months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        return {m: 0.0 for m in months}

    # --- COVID ANOMALY FILTERING (PRECISION MASK) ---
    # We treat Mar-2020 to mid-2022 as outliers (NaN).
    # Recovery began mid-2022, so we keep points from July 2022 onwards.
    temp['y'] = temp['y_raw']
    temp.loc[(temp['ds'] >= '2020-03-01') & (temp['ds'] <= '2022-06-01'), 'y'] = None

    # Apply Log Transformation after masking
    # Use log1p to handle zeros safely
    temp['y'] = np.log1p(temp['y'].astype(float))

    # --- HIGH-PRECISION TUNING ---
    # Check for available regressors in the dataset
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        seasonality_mode='multiplicative',
        changepoint_prior_scale=0.05, # Conservative for income-based metrics
        seasonality_prior_scale=5.0  
    )
    
    # Try to add exogenous regressors if available in the dataframe
    potential_regressors = ['HAS_EVENT', 'Avg_Rainfall_mm', 'Avg_Temperature_C']
    active_regressors = [r for r in potential_regressors if r in df.columns]
    for r in active_regressors:
        model.add_regressor(r)

    model.fit(temp)

    future_dates = pd.date_range(start=f"{selected_year}-01-01", end=f"{selected_year}-12-01", freq='MS')
    future_df = pd.DataFrame({'ds': future_dates})
    
    # Merge regressors for future if possible (using historical averages for that month)
    if active_regressors:
        # Simple historical monthly average for regressors
        df_hist = df.copy()
        df_hist['month'] = pd.to_datetime(df_hist['ds']).dt.month if 'ds' in df_hist.columns else None
        # ... logic for future regressors would go here, but for now we rely on the mean
        for r in active_regressors:
            future_df[r] = df[r].mean()

    forecast = model.predict(future_df)

    # Inverse transform (expm1) to get back to original scale
    result = {row['ds'].strftime('%B'): float(np.expm1(row['yhat'])) for _, row in forecast.iterrows()}
    return result


# ===============================
# TOP-DOWN RECONCILIATION HELPERS
# ===============================

@lru_cache(maxsize=32)
def get_distribution_ratios(category_type):
    """
    Calculate historical contribution ratios for Region or Age.
    Uses Recovery-Phase data (2023-2025) for more modern relevance.
    """
    if category_type == 'region':
        df = df_region.copy()
        # Filter for recent healthy recovery years
        recent = df[df['YEAR'] >= 2023]
        if recent.empty: recent = df
        totals = recent.groupby('REGION')['ARRIVALS'].sum()
    else:
        df = df_age.copy()
        recent = df[df['Year'] >= 2023]
        if recent.empty: recent = df
        totals = recent.groupby('Age')['No Of Tourist'].sum()
    
    total_sum = totals.sum()
    if total_sum == 0: return {}
    
    return (totals / total_sum).to_dict()

def predict_region_proportional(selected_year, total_annual_limit):
    """Breakdown the annual total into regions based on historical ratios."""
    ratios = get_distribution_ratios('region')
    return {region: float(total_annual_limit * ratio) for region, ratio in ratios.items()}

def predict_age_proportional(selected_year, total_annual_limit):
    """Breakdown the annual total into age groups based on historical ratios."""
    ratios = get_distribution_ratios('age')
    return {age: float(total_annual_limit * ratio) for age, ratio in ratios.items()}


@lru_cache(maxsize=128)
def predict_monthly(selected_year):
    """
    Primary Forecasting Engine (The Source of Truth).
    Everything else aligns to this total.
    """
    df = df_month.copy()
    if 'YEAR' in df.columns and 'MONTH' in df.columns and 'TOTAL_ARRIVALS' in df.columns:
        month_map = {
            "January":1, "February":2, "March":3, "April":4, "May":5, "June":6,
            "July":7, "August":8, "September":9, "October":10, "November":11, "December":12
        }
        df['month_num'] = df['MONTH'].str.title().map(month_map)
        df['ds'] = pd.to_datetime(df['YEAR'].astype(str) + "-" + df['month_num'].astype(str) + "-01")
        df['y'] = pd.to_numeric(df['TOTAL_ARRIVALS'], errors='coerce')
    else:
        return {}

    # --- COVID ANOMALY FILTERING (RECOVERY AWARE) ---
    temp = df.copy()
    # Mask Mar 2020 to mid 2022
    temp.loc[(temp['ds'] >= '2020-03-01') & (temp['ds'] <= '2022-06-01'), 'y'] = None

    # Log-Transformation (Guarantee Non-Negative, Stabilize recovery variance)
    temp['y'] = np.log1p(temp['y'].astype(float))

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        seasonality_mode='multiplicative',
        changepoint_prior_scale=0.03, # High stability for national trends
        seasonality_prior_scale=10.0 
    )

    model.fit(temp[['ds', 'y']])

    future = pd.date_range(start=f"{selected_year}-01-01", end=f"{selected_year}-12-01", freq='MS')
    future_df = pd.DataFrame({'ds': future})

    forecast = model.predict(future_df)
    
    # Return Month -> Predicted Count (re-scaled from log)
    results = {row['ds'].strftime('%B'): float(np.expm1(row['yhat'])) for _, row in forecast.iterrows()}
    return results

def predict_income(selected_year, month_truth_data):
    """
    Predict income metrics using predicted arrivals as a baseline.
    Ensure 'Number of tourist arrivals' matches the month_truth_data exactly.
    """
    # Use forecast_metric logic for value and duration (which are independent properties)
    avg_value = forecast_metric_cached("Average value of the Month", selected_year)
    avg_duration = forecast_metric_cached("Average duration of the Month", selected_year)

    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    final = []
    for m in months:
        # Use our primary truth for arrivals
        a = month_truth_data.get(m, 0.0)
        v = avg_value.get(m, 0.0)
        d = avg_duration.get(m, 0.0)

        # Revenue Formula: Count * Spend * Length
        total_income = (a * v * d) / 1_000_000 if (a and v and d) else 0.0

        final.append({
            "Month": m,
            "Number of tourist arrivals": round(a),
            "Average value of the Month": round(v, 2),
            "Average duration of the Month": round(d, 2),
            "Total value (USD Mn)": round(total_income, 2)
        })

    return final
