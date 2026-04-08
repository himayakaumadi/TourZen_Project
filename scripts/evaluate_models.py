# scripts/evaluate_models.py
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    median_absolute_error
)
from prophet import Prophet


# -----------------------------
# PATHS
# -----------------------------
BASE = Path(r"C:\Users\DELL\Downloads\University\DataManagementProject\tourzen_app")
CLEAN = BASE / "data_cleaned"
OUT = BASE / "model_evaluation"
PLOTS = OUT / "plots"

OUT.mkdir(exist_ok=True, parents=True)
PLOTS.mkdir(exist_ok=True, parents=True)


# -----------------------------
# LOAD CLEAN DATASETS
# -----------------------------
df_region = pd.read_csv(CLEAN / "training_dataset.csv")

df_age = pd.read_csv(CLEAN / "tourist_arrivals_by_age_cleaned.csv")

df_month = pd.read_csv(CLEAN / "national_monthly_arrivals_fixed_cleaned.csv")

df_income = pd.read_csv(CLEAN / "tourism_income_combined_cleaned.csv")


# -----------------------------
# METRIC FUNCTIONS
# -----------------------------
def smape(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    denom[denom == 0] = 1
    return 100 * np.mean(2 * np.abs(y_pred - y_true) / denom)


def mape_ignore_zero(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan
    return 100 * np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask]))


def compute_metrics(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "R2": r2_score(y_true, y_pred),
        "MedAE": median_absolute_error(y_true, y_pred),
        "MAPE(%)": mape_ignore_zero(y_true, y_pred),
        "SMAPE(%)": smape(y_true, y_pred),
    }


summary_rows = []


# ============================================================
# 1) REGION MODEL — RandomForestRegressor
# ============================================================
print("\n=== REGION MODEL EVALUATION ===")

df_r = df_region.groupby(["YEAR", "REGION"])["ARRIVALS"].sum().reset_index()

for region in sorted(df_r["REGION"].unique()):
    dfr = df_r[df_r["REGION"] == region].sort_values("YEAR")
    X = dfr[["YEAR"]].values
    y = dfr["ARRIVALS"].values

    if len(y) < 5:
        continue

    # train/test split (last 20% for testing)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = compute_metrics(y_test, y_pred)
    summary_rows.append({"Model": "Region_RF", "Segment": region, **metrics})

    # PLOT
    plt.figure(figsize=(8, 4))
    plt.plot(dfr["YEAR"], y, label="Actual", marker="o")
    plt.plot(dfr["YEAR"].iloc[split_idx:], y_pred,
             label="Predicted (Test)", marker="x")
    plt.title(f"Region Model — {region}")
    plt.xlabel("Year")
    plt.ylabel("Arrivals")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS / f"region_{region.replace(' ', '_')}.png")
    plt.close()


# ============================================================
# 2) AGE MODEL — Linear Regression
# ============================================================
print("\n=== AGE MODEL EVALUATION ===")

for age_cat in sorted(df_age["Age"].unique()):
    dfa = df_age[df_age["Age"] == age_cat].sort_values("Year")

    X = dfa[["Year"]].values
    y = dfa["No Of Tourist"].astype(float).values

    if len(y) < 5:
        continue

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = compute_metrics(y_test, y_pred)
    summary_rows.append({"Model": "Age_LR", "Segment": age_cat, **metrics})

    # plot
    plt.figure(figsize=(8, 4))
    plt.plot(dfa["Year"], y, label="Actual", marker="o")
    plt.plot(dfa["Year"].iloc[split_idx:], y_pred,
             label="Predicted (Test)", marker="x")
    plt.title(f"Age Model — {age_cat}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS / f"age_{age_cat.replace(' ', '_')}.png")
    plt.close()


# ============================================================
# 3) MONTHLY ARRIVALS — Prophet
# ============================================================
print("\n=== MONTHLY ARRIVALS PROPHET EVALUATION ===")

dfm = df_month.copy()
month_map = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12
}
dfm["month_num"] = dfm["MONTH"].map(month_map)
dfm["ds"] = pd.to_datetime(dfm["YEAR"].astype(str) + "-" + dfm["month_num"].astype(str) + "-01")
dfm["y"] = dfm["TOTAL_ARRIVALS"]

dfm = dfm.dropna(subset=["ds", "y"]).sort_values("ds")

split_idx = int(len(dfm) * 0.8)
train, test = dfm.iloc[:split_idx], dfm.iloc[split_idx:]

m = Prophet(yearly_seasonality=True, weekly_seasonality=False)
m.fit(train[["ds", "y"]])

forecast = m.predict(test[["ds"]])
y_pred = forecast["yhat"].values
y_test = test["y"].values

metrics = compute_metrics(y_test, y_pred)
summary_rows.append({"Model": "Prophet_Monthly", "Segment": "National", **metrics})

# plot
plt.figure(figsize=(10, 4))
plt.plot(dfm["ds"], dfm["y"], label="Actual")
plt.plot(test["ds"], y_pred, label="Predicted (Test)", marker="x")
plt.title("Prophet Monthly Arrivals")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(PLOTS / "monthly_arrivals_prophet.png")
plt.close()


# ============================================================
# 4) TOURISM INCOME — Prophet on Arrivals Component
# ============================================================
print("\n=== TOURISM INCOME PROPHET EVALUATION ===")

dfi = df_income.copy()
dfi["Month"] = dfi["Month"].str.title()
dfi["month_num"] = dfi["Month"].map(month_map)
dfi["ds"] = pd.to_datetime(dfi["Year"].astype(str) + "-" + dfi["month_num"].astype(str) + "-01")
dfi["y"] = dfi["Number of tourist arrivals"]

dfi = dfi.dropna(subset=["ds", "y"]).sort_values("ds")

split_idx = int(len(dfi) * 0.8)
train, test = dfi.iloc[:split_idx], dfi.iloc[split_idx:]

m2 = Prophet(yearly_seasonality=True, weekly_seasonality=False)
m2.fit(train[["ds", "y"]])

forecast2 = m2.predict(test[["ds"]])
y_pred = forecast2["yhat"].values
y_test = test["y"].values

metrics = compute_metrics(y_test, y_pred)
summary_rows.append({"Model": "Prophet_Income_Arrivals", "Segment": "Income Arrivals", **metrics})

# plot
plt.figure(figsize=(10, 4))
plt.plot(dfi["ds"], dfi["y"], label="Actual")
plt.plot(test["ds"], y_pred, label="Predicted (Test)", marker="x")
plt.title("Tourism Income — Arrivals Component")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(PLOTS / "income_arrivals_prophet.png")
plt.close()


# ============================================================
# SAVE SUMMARY CSV
# ============================================================
df_summary = pd.DataFrame(summary_rows)
df_summary.to_csv(OUT / "model_accuracy_summary.csv", index=False)

print("\n=== DONE ===")
print("Saved accuracy summary ->", OUT / "model_accuracy_summary.csv")
print("Saved plots ->", PLOTS)
