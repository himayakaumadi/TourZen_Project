# ===================================================
#   Hybrid Prophet + XGBoost Ensemble Forecaster
#   100% FIXED VERSION — Works with TourZen Dataset
# ===================================================

import os
import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --------------------------
# PATH CONFIG
# --------------------------
BASE = os.path.dirname(__file__)
INPUT_FILE = os.path.abspath(os.path.join(BASE, "..", "data_cleaned", "training_dataset.csv"))
OUT_FILE = os.path.abspath(os.path.join(BASE, "..", "data_cleaned", "forecast_ensemble.csv"))

print("=== Hybrid Prophet + XGBoost Ensemble Training ===")

# --------------------------
# LOAD DATA
# --------------------------
def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Training file not found: {path}")
    df = pd.read_csv(path, parse_dates=["DATE"])
    return df

df_raw = load_data(INPUT_FILE)

# --------------------------
# CLEAN + PREPARE
# --------------------------
df = df_raw.copy()

df_nat = df.groupby("DATE", as_index=False).agg({
    "ARRIVALS": "sum",
    "HAS_EVENT": "mean",
    "Avg_Rainfall_mm": "mean",
    "Avg_Temperature_C": "mean",
    "MONTH_SIN": "mean",
    "MONTH_COS": "mean"
})

df_nat = df_nat.sort_values("DATE")

# Lag features
df_nat["lag_1"]  = df_nat["ARRIVALS"].shift(1)
df_nat["lag_12"] = df_nat["ARRIVALS"].shift(12)

df_nat = df_nat.dropna().reset_index(drop=True)

print("\nData for modeling (head):")
print(df_nat.head())

# --------------------------
# TRAIN PROPHET
# --------------------------
print("\n>>> Training Prophet on national aggregated data")

prophet_df = df_nat.rename(columns={"DATE": "ds", "ARRIVALS": "y"})
prophet_model = Prophet(
    yearly_seasonality=True,
    seasonality_mode="additive"
)

for r in ["HAS_EVENT", "Avg_Rainfall_mm", "Avg_Temperature_C", "MONTH_SIN", "MONTH_COS"]:
    prophet_model.add_regressor(r)

prophet_model.fit(prophet_df)

# --------------------------------------------
# FIX: Create future ONLY for historical range
# --------------------------------------------
min_date = df_nat["DATE"].min()
max_date = df_nat["DATE"].max()

future_hist = prophet_model.make_future_dataframe(periods=0, freq="MS")
future_hist = future_hist[(future_hist["ds"] >= min_date) & (future_hist["ds"] <= max_date)]

# Build monthly averages
prophet_df["MONTH_NUM"] = prophet_df["ds"].dt.month
monthly_ref = prophet_df.groupby("MONTH_NUM", as_index=False).agg({
    "HAS_EVENT": "mean",
    "Avg_Rainfall_mm": "mean",
    "Avg_Temperature_C": "mean",
    "MONTH_SIN": "mean",
    "MONTH_COS": "mean"
})

# Fill regressors for historical predictions
future_hist["MONTH_NUM"] = future_hist["ds"].dt.month
future_hist = future_hist.merge(monthly_ref, on="MONTH_NUM", how="left")
future_hist = future_hist.drop(columns=["MONTH_NUM"])

prophet_hist_pred = prophet_model.predict(future_hist)
prophet_hist_pred = prophet_hist_pred[["ds", "yhat"]].rename(columns={"yhat": "prophet_pred"})

# --------------------------
# TRAIN XGBOOST
# --------------------------
print("\n>>> Training XGBoost on lag + regressors")

FEATURES = ["HAS_EVENT", "Avg_Rainfall_mm", "Avg_Temperature_C",
            "MONTH_SIN", "MONTH_COS", "lag_1", "lag_12"]

train = df_nat.dropna()
X = train[FEATURES]
y = train["ARRIVALS"]

xgb_model = xgb.XGBRegressor(
    n_estimators=400,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.9,
    colsample_bytree=0.9,
    reg_lambda=1.0
)
xgb_model.fit(X, y)

# XGB predictions for historical dates
xgb_hist_pred = train[["DATE"]].copy()
xgb_hist_pred["xgb_pred"] = xgb_model.predict(X)

# --------------------------
# MERGE HISTORICAL PREDICTIONS
# --------------------------
merged = prophet_hist_pred.merge(
    xgb_hist_pred.rename(columns={"DATE": "ds"}),
    on="ds",
    how="inner"
)

# Match true values
merged["DATE"] = merged["ds"]
merged = merged.merge(df_nat[["DATE", "ARRIVALS"]], on="DATE", how="left")
merged = merged.rename(columns={"ARRIVALS": "y_true"})

# --------------------------
# FILTER rows where all values exist
# --------------------------
hist = merged.dropna(subset=["y_true", "prophet_pred", "xgb_pred"])

# --------------------------
# ENSEMBLE WEIGHTS
# --------------------------
print("\n>>> Calculating dynamic ensemble weights")

prophet_mae = mean_absolute_error(hist["y_true"], hist["prophet_pred"])
xgb_mae     = mean_absolute_error(hist["y_true"], hist["xgb_pred"])

prophet_w = 1 / prophet_mae
xgb_w = 1 / xgb_mae
total = prophet_w + xgb_w

prophet_w /= total
xgb_w     /= total

print(f"Ensemble weights → Prophet: {prophet_w:.3f}, XGB: {xgb_w:.3f}")

# --------------------------
# ENSEMBLE PREDICTIONS
# --------------------------
hist["ensemble_pred"] = (
    prophet_w * hist["prophet_pred"] +
    xgb_w     * hist["xgb_pred"]
)

# --------------------------
# ACCURACY
# --------------------------
print("\n===============================")
print("📊 FINAL ENSEMBLE MODEL ACCURACY")
print("===============================")

mae  = mean_absolute_error(hist["y_true"], hist["ensemble_pred"])
rmse = mean_squared_error(hist["y_true"], hist["ensemble_pred"]) ** 0.5
r2   = r2_score(hist["y_true"], hist["ensemble_pred"])
mape = np.mean(np.abs((hist["y_true"] - hist["ensemble_pred"]) / hist["y_true"])) * 100

print(f"MAE  : {mae:,.2f}")
print(f"RMSE : {rmse:,.2f}")
print(f"R²   : {r2:.3f}")
print(f"MAPE : {mape:.2f}%")
print("===============================\n")

# --------------------------
# SAVE HISTORICAL ENSEMBLE
# --------------------------
merged.to_csv(OUT_FILE, index=False)
print(f"✅ Saved historical ensemble forecast: {OUT_FILE}")

# --------------------------
# BUILD TRUE FUTURE 12-MONTH PREDICTIONS
# --------------------------
print("\n>>> Generating real future forecast (next 12 months)")

# Predict until December 2035
last_date = df_nat["DATE"].max()
target_end = pd.to_datetime("2035-12-01")
months_to_predict = (target_end.year - last_date.year) * 12 + (target_end.month - last_date.month)

future_real = prophet_model.make_future_dataframe(periods=months_to_predict, freq="MS")


future_real["MONTH_NUM"] = future_real["ds"].dt.month
future_real = future_real.merge(monthly_ref, on="MONTH_NUM", how="left")
future_real = future_real.drop(columns=["MONTH_NUM"])

future_pred = prophet_model.predict(future_real)
future_pred = future_pred[["ds", "yhat"]].rename(columns={"yhat": "prophet_pred"})

# Save future forecast
future_outfile = os.path.join(os.path.dirname(OUT_FILE), "forecast_future_ensemble_prophet.csv")
future_pred.to_csv(future_outfile, index=False)

print(f"✅ Saved future 12-month forecast: {future_outfile}")
print("\n🎉 Ensemble model training completed successfully!")
