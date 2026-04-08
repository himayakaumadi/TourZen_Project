import os
import sys
import pandas as pd
from firebase_admin import db

# ==========================================
# 1. INITIALIZE FIREBASE
# ==========================================
# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

try:
    import firebase_config   # This initializes Firebase
    print("✔ Firebase initialized.")
except Exception as e:
    print("❌ Firebase initialization failed:", e)
    sys.exit(1)

# ==========================================
# 2. FIND FORECAST FILE AUTOMATICALLY
# ==========================================
DATA_CLEANED_DIR = os.path.join(PROJECT_ROOT, "data_cleaned")

POSSIBLE_FILES = [
    "forecast_prophet.csv",
    "forecast_ensemble.csv",
    "forecast_future_ensemble_prophet.csv"
]

FORECAST_FILE = None

for fname in POSSIBLE_FILES:
    fpath = os.path.join(DATA_CLEANED_DIR, fname)
    if os.path.exists(fpath):
        FORECAST_FILE = fpath
        print(f"📌 Using forecast file: {fname}")
        break

if FORECAST_FILE is None:
    print("❌ No forecast CSV found in data_cleaned/")
    print("Expected one of:", POSSIBLE_FILES)
    sys.exit(1)

print(f"Full path: {FORECAST_FILE}")

# ==========================================
# 3. FIREBASE TARGET PATH
# ==========================================
FIREBASE_PATH = "forecasts/prophet"

# ==========================================
# 4. UPLOAD FUNCTION
# ==========================================
def upload_forecast():
    print(f"\n🚀 Uploading forecasts to Firebase: /{FIREBASE_PATH}/")

    # Load CSV
    df = pd.read_csv(FORECAST_FILE)

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    required_cols = {"ds", "yhat"}
    if not required_cols.issubset(df.columns):
        print("❌ Forecast CSV missing required columns!")
        print("Required:", required_cols)
        print("CSV has:", df.columns.tolist())
        return

    ref = db.reference(FIREBASE_PATH)

    upload_count = 0

    for _, row in df.iterrows():
        ds_value = str(row["ds"]).split(" ")[0]   # → YYYY-MM-DD
        if len(ds_value) < 7:
            continue

        date_key = ds_value[:7]  # → YYYY-MM

        # JSON safe payload
        entry = {
            "yhat": float(row.get("yhat", 0)),
            "yhat_lower": float(row.get("yhat_lower", 0)),
            "yhat_upper": float(row.get("yhat_upper", 0))
        }

        print(f"⬆ Uploading {date_key} → {entry}")

        ref.child(date_key).set(entry)
        upload_count += 1

    print("\n=================================")
    print(f"✅ Upload complete! Total months uploaded: {upload_count}")
    print(f"📍 Firebase Path: /{FIREBASE_PATH}/")
    print("=================================\n")


# ==========================================
# 5. SCRIPT ENTRY POINT
# ==========================================
if __name__ == "__main__":
    upload_forecast()
