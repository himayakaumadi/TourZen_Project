# scripts/prepare_training_data.py
import os
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------
# FIXED PATHS – ALWAYS CORRECT LOCATION (works no matter where you run)
# ---------------------------------------------------------------------
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data_cleaned"))
ARR_FILE = os.path.join(BASE, "monthly_tourism_cleaned.csv")
EVENT_FILE = os.path.join(BASE, "Event_Month_Tagged.csv")
WEATHER_PROVINCE = os.path.join(BASE, "Province_WeatherMonthly.csv")
OUT_FILE = os.path.join(BASE, "training_dataset.csv")

# Month mapping
MONTH_ORDER = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]
MONTH2NUM = {m: i+1 for i, m in enumerate(MONTH_ORDER)}


# ---------------------------------------------------------------------
# SAFELY CONVERT TO NUMBER (removes impossible values)
# ---------------------------------------------------------------------
def safe_number(value):
    try:
        value = float(value)
        if value < 0 or value > 1_000_000:   # remove garbage values
            return np.nan
        return value
    except:
        return np.nan


# ---------------------------------------------------------------------
# MAIN PROCESSING PIPELINE
# ---------------------------------------------------------------------
def main():

    print("📥 Loading:", ARR_FILE)
    print("Exists:", os.path.exists(ARR_FILE))

    if not os.path.exists(ARR_FILE):
        raise FileNotFoundError(f"❌ Missing {ARR_FILE}")
    if not os.path.exists(EVENT_FILE):
        raise FileNotFoundError(f"❌ Missing {EVENT_FILE}")
    if not os.path.exists(WEATHER_PROVINCE):
        raise FileNotFoundError(f"❌ Missing {WEATHER_PROVINCE}")

    # ---------------------------
    # 1️⃣ Load monthly arrivals
    # ---------------------------
    df = pd.read_csv(ARR_FILE)
    df.columns = [c.strip().upper() for c in df.columns]

    required_cols = ["YEAR", "REGION", "COUNTRY", "MONTH", "ARRIVALS"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"❌ Column {col} missing in monthly_tourism_cleaned.csv")

    # Normalize month
    df["MONTH"] = df["MONTH"].str.capitalize()

    # Clean ARRIVALS
    df["ARRIVALS"] = df["ARRIVALS"].apply(safe_number)
    df = df.dropna(subset=["ARRIVALS"])
    df["ARRIVALS"] = df["ARRIVALS"].astype(int)

    # ---------------------------
    # 2️⃣ Load Event Tag File
    # ---------------------------
    ev = pd.read_csv(EVENT_FILE)
    ev.columns = [c.strip().title() for c in ev.columns]
    ev = ev.rename(columns={"Month":"MONTH", "Has_Event":"HAS_EVENT"})
    ev["MONTH"] = ev["MONTH"].str.capitalize()
    ev["HAS_EVENT"] = ev["HAS_EVENT"].astype(str).str.lower().map({
        "yes": 1,
        "no": 0
    }).fillna(0).astype(int)

    # ---------------------------
    # 3️⃣ Load Weather (Province-level)
    # ---------------------------
    w = pd.read_csv(WEATHER_PROVINCE)
    w["Month"] = w["Month"].str.capitalize()
    w = w.groupby("Month", as_index=False).agg(
        Avg_Temperature_C=("Avg_Temperature_C", "mean"),
        Avg_Rainfall_mm=("Avg_Rainfall_mm", "mean")
    )
    w = w.rename(columns={"Month": "MONTH"})

    # ---------------------------
    # 4️⃣ Merge All Datasets
    # ---------------------------
    m = df.merge(ev, on="MONTH", how="left").merge(w, on="MONTH", how="left")
    m["HAS_EVENT"] = m["HAS_EVENT"].fillna(0).astype(int)

    # Safely clean weather numbers
    m["Avg_Temperature_C"] = m["Avg_Temperature_C"].apply(safe_number).fillna(0)
    m["Avg_Rainfall_mm"] = m["Avg_Rainfall_mm"].apply(safe_number).fillna(0)

    # ---------------------------
    # 5️⃣ Month number + Cyclical encoding
    # ---------------------------
    m["MONTH_NUM"] = m["MONTH"].map(MONTH2NUM).astype(int)

    m["MONTH_SIN"] = np.sin(2 * np.pi * m["MONTH_NUM"] / 12)
    m["MONTH_COS"] = np.cos(2 * np.pi * m["MONTH_NUM"] / 12)

    # ---------------------------
    # 6️⃣ Build DATE column
    # ---------------------------
    m["DATE"] = pd.to_datetime(
        m["YEAR"].astype(str) + "-" + m["MONTH_NUM"].astype(str) + "-01"
    )

    # Final sorting
    m = m.sort_values(["DATE", "COUNTRY", "REGION"]).reset_index(drop=True)

    # ---------------------------
    # 7️⃣ Save Output
    # ---------------------------
    m.to_csv(OUT_FILE, index=False)

    print("\n✅ Clean training dataset saved successfully!")
    print("📄 Location:", OUT_FILE)
    print("\n🔍 Sample Output:")
    print(m.head())


if __name__ == "__main__":
    main()
