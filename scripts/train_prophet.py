# scripts/train_prophet.py
import os
import pandas as pd
from prophet import Prophet

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data_cleaned"))
IN_FILE = os.path.join(BASE, "training_dataset.csv")
OUT_FILE = os.path.join(BASE, "forecast_prophet.csv")

FORECAST_HORIZON = 12  # months
AGGREGATE_NATIONAL = True


def build_and_forecast(df_in, label):

    print(f"📌 Training Prophet model for series: {label}")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="additive"
    )

    # Add regressors
    for r in ["HAS_EVENT", "Avg_Rainfall_mm", "Avg_Temperature_C"]:
        model.add_regressor(r)

    # Train
    model.fit(df_in[["ds", "y", "HAS_EVENT", "Avg_Rainfall_mm", "Avg_Temperature_C"]])

    # Generate future dates
    # Predict until December 2035
    target_end = pd.to_datetime("2035-12-01")
    last_date = df_in["ds"].max()

    months_to_predict = (target_end.year - last_date.year) * 12 + (target_end.month - last_date.month)

    future = model.make_future_dataframe(periods=months_to_predict, freq="MS")


    # Extract month number
    future["MONTH_NUM"] = future["ds"].dt.month

    # Build monthly average regressor table
    month_ref = df_in.copy()
    month_ref["MONTH_NUM"] = month_ref["ds"].dt.month

    month_ref = month_ref.groupby("MONTH_NUM", as_index=False).agg(
        HAS_EVENT=("HAS_EVENT", "mean"),
        Avg_Rainfall_mm=("Avg_Rainfall_mm", "mean"),
        Avg_Temperature_C=("Avg_Temperature_C", "mean")
    )

    # Merge MONTH_NUM onto future rows
    future = future.merge(month_ref, on="MONTH_NUM", how="left")

    # Ensure ds stays correct
    future["ds"] = pd.to_datetime(future["ds"])

    # Predict
    forecast = model.predict(future)

    out = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    out["series"] = label

    return out


def main():

    print(f"\n📥 Loading training dataset: {IN_FILE}")

    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(f"❌ Missing file: {IN_FILE}")

    df = pd.read_csv(IN_FILE, parse_dates=["DATE"])
    print("✔ Training dataset loaded.")

    base_cols = [
        "DATE", "ARRIVALS", "HAS_EVENT",
        "Avg_Rainfall_mm", "Avg_Temperature_C",
        "MONTH_SIN", "MONTH_COS", "COUNTRY"
    ]

    # Clean & validate
    for col in base_cols:
        if col not in df.columns:
            raise ValueError(f"❌ Missing column in dataset: {col}")

    outputs = []

    if AGGREGATE_NATIONAL:
        print("\n🔄 Aggregating national monthly arrivals...")

        agg = df.groupby("DATE", as_index=False).agg(
            ARRIVALS=("ARRIVALS", "sum"),
            HAS_EVENT=("HAS_EVENT", "mean"),
            Avg_Rainfall_mm=("Avg_Rainfall_mm", "mean"),
            Avg_Temperature_C=("Avg_Temperature_C", "mean")
        )

        prophet_df = agg.rename(columns={"DATE": "ds", "ARRIVALS": "y"})
        out = build_and_forecast(prophet_df, "SriLanka_Total")
        outputs.append(out)

    else:
        for country, g in df.groupby("COUNTRY"):

            prophet_df = g.rename(columns={"DATE": "ds", "ARRIVALS": "y"})
            out = build_and_forecast(prophet_df, f"Country:{country}")
            outputs.append(out)

    final = pd.concat(outputs, ignore_index=True)
    final.to_csv(OUT_FILE, index=False)

    print("\n✅ Prophet forecast saved to:")
    print(OUT_FILE)
    print(final.tail())


if __name__ == "__main__":
    main()
