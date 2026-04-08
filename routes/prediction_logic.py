import pandas as pd
import numpy as np
from prophet import Prophet
from functools import lru_cache
import os

# Set project root relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CLEANED = os.path.join(BASE_DIR, "data_cleaned")
DATA_RAW = os.path.join(BASE_DIR, "data_raw")

df_month = pd.read_csv(os.path.join(DATA_CLEANED, "national_monthly_arrivals_fixed.csv"))
df_month.columns = df_month.columns.str.strip().str.upper()
if 'TOTAL_ARRIVALS' not in df_month.columns:
    for c in df_month.columns:
        if 'ARRIV' in c:
            df_month.rename(columns={c: 'TOTAL_ARRIVALS'}, inplace=True)

df_region = pd.read_csv(os.path.join(DATA_CLEANED, "training_dataset.csv"))
df_age = pd.read_excel(os.path.join(DATA_RAW, "TouristArrivalByAge.xlsx"))
df_income = pd.read_csv(os.path.join(DATA_CLEANED, "training_dataset.csv")) # Re-using as fallback

from sklearn.linear_model import LinearRegression

@lru_cache(maxsize=32)
def get_distribution_ratios(category_type, target_year):
    """
    Predict the market share (%) for each category in a target year.
    Uses Linear Regression on historical annual shares to find trends.
    """
    if category_type == 'region':
        df = df_region.copy()
        y_col, c_col, v_col = 'YEAR', 'REGION', 'ARRIVALS'
    else:
        df = df_age.copy()
        df.columns = df.columns.str.strip()
        c_col = [c for c in df.columns if 'age' in c.lower()][0]
        v_col = [c for c in df.columns if 'no' in c.lower() and 'tourist' in c.lower()][0]
        y_col = [c for c in df.columns if 'year' in c.lower()][0]
    
    # 1. Aggregate Arrivals by Year and Category
    annual_data = df.groupby([y_col, c_col])[v_col].sum().unstack(fill_value=0)
    
    # 2. Calculate Annual Market Share
    annual_totals = annual_data.sum(axis=1)
    # Avoid div by zero
    shares_history = annual_data.divide(annual_totals, axis=0).fillna(0)
    
    # 3. Predict Share for Target Year using Linear Regression
    X = shares_history.index.values.reshape(-1, 1) # Years
    predicted_shares = {}
    
    for category in shares_history.columns:
        Y = shares_history[category].values.reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, Y)
        
        # Predict 2027 or target_year
        pred_share = model.predict([[target_year]])[0][0]
        # Keep shares non-negative
        predicted_shares[category] = max(0.001, pred_share) # floor at 0.1% to prevent zero-slices
        
    # 4. Normalize (Ensure sum == 1.0)
    total_pred = sum(predicted_shares.values())
    normalized_shares = {c: s / total_pred for c, s in predicted_shares.items()}
    
    return normalized_shares

@lru_cache(maxsize=128)
def predict_monthly(selected_year):
    df = df_month.copy()
    month_map = {
        "January":1, "February":2, "March":3, "April":4, "May":5, "June":6,
        "July":7, "August":8, "September":9, "October":10, "November":11, "December":12
    }
    df['month_num'] = df['MONTH'].str.title().map(month_map)
    df['ds'] = pd.to_datetime(df['YEAR'].astype(str) + "-" + df['month_num'].astype(str) + "-01")
    df['y'] = pd.to_numeric(df['TOTAL_ARRIVALS'], errors='coerce')

    # Modern Era Filtering: Only use data from July 2022 onwards (The "New Normal")
    # This eliminates the pandemic gap and provides a much cleaner trend line for 2027.
    df = df[df['ds'] >= '2022-07-01'].copy()
    df['y'] = np.log1p(df['TOTAL_ARRIVALS'].astype(float))

    # Ultra-Precision Parameters (Modern Era)
    model = Prophet(
        growth='linear',
        yearly_seasonality=True,
        weekly_seasonality=False,
        seasonality_mode='multiplicative',
        changepoint_prior_scale=0.01,   # Very stable (was 0.05) since the recovery trend is linear
        seasonality_prior_scale=10.0,
        changepoint_range=0.9
    )
    model.fit(df[['ds', 'y']])

    future = pd.date_range(start=f"{selected_year}-01-01", end=f"{selected_year}-12-01", freq='MS')
    future_df = pd.DataFrame({'ds': future})
    forecast = model.predict(future_df)
    
    return {row['ds'].strftime('%B'): float(np.expm1(row['yhat'])) for _, row in forecast.iterrows()}

def forecast_metric(df, metric, selected_year):
    temp = df.copy()
    month_map = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
    temp['Month'] = temp['Month'].str.title()
    temp['month_num'] = temp['Month'].map(month_map)
    temp['ds'] = pd.to_datetime(temp['Year'].astype(str) + "-" + temp['month_num'].astype(str) + "-01")
    temp['y_raw'] = pd.to_numeric(temp[metric], errors='coerce')
    temp = temp.dropna(subset=['ds', 'y_raw'])
    
    if temp.empty:
        return {m: 0.0 for m in month_map.keys()}

    temp['y'] = temp['y_raw']
    temp.loc[(temp['ds'] >= '2020-03-01') & (temp['ds'] <= '2022-06-01'), 'y'] = None
    temp['y'] = np.log1p(temp['y'].astype(float))

    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, seasonality_mode='multiplicative', changepoint_prior_scale=0.05, seasonality_prior_scale=5.0)
    model.fit(temp[['ds', 'y']])

    future_dates = pd.date_range(start=f"{selected_year}-01-01", end=f"{selected_year}-12-01", freq='MS')
    future_df = pd.DataFrame({'ds': future_dates})
    forecast = model.predict(future_df)
    return {row['ds'].strftime('%B'): float(np.expm1(row['yhat'])) for _, row in forecast.iterrows()}

def predict_region_proportional(selected_year, total_annual_limit):
    """Breakdown the annual total into regions based on historical ratios."""
    ratios = get_distribution_ratios('region', selected_year)
    return {region: float(total_annual_limit * ratio) for region, ratio in ratios.items()}

def predict_age_proportional(selected_year, total_annual_limit):
    """Breakdown the annual total into age groups based on historical ratios."""
    ratios = get_distribution_ratios('age', selected_year)
    return {age: float(total_annual_limit * ratio) for age, ratio in ratios.items()}

def predict_income(selected_year, month_truth_data):
    """
    Predict income metrics using predicted arrivals as a baseline.
    Ensure 'Number of tourist arrivals' matches the month_truth_data exactly.
    """
    # Use forecast_metric logic for value and duration (which are independent properties)
    avg_value = forecast_metric(df_income, "Average value of the Month", selected_year)
    avg_duration = forecast_metric(df_income, "Average duration of the Month", selected_year)

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
