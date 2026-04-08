# scripts/evaluate_model_accuracy_national.py
import os
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE = os.path.join(os.path.dirname(__file__), "..", "data_cleaned")
forecast_file = os.path.join(BASE, "forecast_prophet.csv")
national_file = os.path.join(BASE, "national_monthly_arrivals.csv")
out_accuracy = os.path.join(BASE, "forecast_accuracy.csv")

# Check files
for p in [forecast_file, national_file]:
    if not os.path.exists(p):
        print("Missing file:", p)
        raise SystemExit(1)

# Load
f = pd.read_csv(forecast_file, dtype=str)
n = pd.read_csv(national_file, dtype=str)

# Clean forecast
f.columns = f.columns.str.upper().str.strip()

# If forecast contains a 'SERIES' column, try to select national series
# (common value seen: 'SriLanka_Total' - case-insensitive)
if "SERIES" in f.columns:
    possible = f["SERIES"].unique().tolist()
    print("Forecast SERIES values:", possible[:10])
    # Try selecting any series name that contains "SRI" and "TOTAL" (safe heuristic)
    mask_series = f["SERIES"].str.upper().str.contains("SRI") & f["SERIES"].str.upper().str.contains("TOTAL")
    if mask_series.any():
        f = f[mask_series].copy()
        print("Selected forecast rows where SERIES looks like national total.")
    else:
        print("No obvious national-series filter applied. Using entire forecast file (ensure it's national).")

# Parse ds to YEAR+MONTH
f["DS"] = pd.to_datetime(f["DS"], errors="coerce")
f["YEAR"] = f["DS"].dt.year
f["MONTH"] = f["DS"].dt.strftime("%B").str.upper()
f["YHAT"] = pd.to_numeric(f["YHAT"], errors="coerce")

# Clean national totals
n.columns = n.columns.str.upper().str.strip()
n["YEAR"] = pd.to_numeric(n["YEAR"], errors="coerce").astype(int)
n["MONTH"] = n["MONTH"].astype(str).str.upper()
n["TOTAL_ARRIVALS"] = pd.to_numeric(n["TOTAL_ARRIVALS"], errors="coerce")

# Merge on YEAR+MONTH (inner)
merged = pd.merge(f[["YEAR","MONTH","YHAT"]], n, on=["YEAR","MONTH"], how="inner")

if merged.empty:
    print("Merged dataset is empty. Check YEAR/MONTH alignment between forecast and national totals.")
    raise SystemExit(1)

# Drop rows with NaN
merged = merged.dropna(subset=["YHAT", "TOTAL_ARRIVALS"])

y_true = merged["TOTAL_ARRIVALS"].astype(float).values
y_pred = merged["YHAT"].astype(float).values

# Remove rows where actual = 0 for MAPE
mask = y_true != 0
y_true_mape = y_true[mask]
y_pred_mape = y_pred[mask]

mae = mean_absolute_error(y_true, y_pred)
rmse = np.sqrt(mean_squared_error(y_true, y_pred))
mape = np.mean(np.abs((y_true_mape - y_pred_mape) / y_true_mape)) * 100 if len(y_true_mape)>0 else np.nan
r2 = r2_score(y_true, y_pred)

accuracy = 100 - mape if not np.isnan(mape) else np.nan

print("====================================")
print("📊  NATIONAL MODEL EVALUATION")
print("====================================")
print(f"Rows merged: {len(merged)}")
print(f"✔ MAE   : {mae:.2f}")
print(f"✔ RMSE  : {rmse:.2f}")
print(f"✔ MAPE  : {mape:.2f}%")
print(f"✔ R²    : {r2:.3f}")
print("------------------------------------")
print(f"🎯 Forecast Accuracy: {accuracy:.2f}%")
print("====================================")

# Save csv for dashboard
out_df = pd.DataFrame({
    "Metric": ["MAE", "RMSE", "MAPE", "R2", "Accuracy"],
    "Value": [mae, rmse, mape, r2, accuracy]
})
out_df.to_csv(out_accuracy, index=False)
print("Saved accuracy metrics to:", out_accuracy)
