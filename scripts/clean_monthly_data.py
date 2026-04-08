import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import os

# === Paths ===
INPUT_FILE = "../data_raw/TouristsArrivalByCountry.xlsx"
OUTPUT_FILE = "../data_cleaned/monthly_tourism_cleaned.csv"

# === Firebase Initialization ===
if not firebase_admin._apps:
    cred = credentials.Certificate("../tourzen-firebase-adminsdk.json")  # Adjust if JSON is in root
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://tourzen-2ab15-default-rtdb.asia-southeast1.firebasedatabase.app"
    })

# === Load Excel ===
df = pd.read_excel(INPUT_FILE)
df.columns = df.columns.str.strip()  # Remove trailing spaces
print("✅ Loaded file. Columns detected:", list(df.columns))

# === Drop TOTAL column if present ===
if "TOTAL" in df.columns:
    df = df.drop(columns=["TOTAL"])
    print("🧹 Dropped TOTAL column")

# === Convert wide format to long format ===
month_columns = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", 
                 "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

df_long = df.melt(id_vars=["YEAR", "REGION", "COUNTRY"], 
                  value_vars=month_columns,
                  var_name="MONTH",
                  value_name="ARRIVALS")

# === Capitalize Month Names ===
df_long["MONTH"] = df_long["MONTH"].str.capitalize()

# === Save Cleaned File ===
os.makedirs("../data_cleaned/", exist_ok=True)
df_long.to_csv(OUTPUT_FILE, index=False)
print(f"💾 Saved cleaned dataset to: {OUTPUT_FILE}")
print(df_long.head())

# === Upload to Firebase ===
ref = db.reference("monthly_arrivals")
uploaded_count = 0

for _, row in df_long.iterrows():
    data = {
        "year": int(row["YEAR"]),
        "region": row["REGION"],
        "country": row["COUNTRY"],
        "month": row["MONTH"],
        "arrivals": int(row["ARRIVALS"]) if not pd.isna(row["ARRIVALS"]) else None
    }
    ref.push(data)
    uploaded_count += 1

print(f"🚀 Uploaded {uploaded_count} records to Firebase (monthly_arrivals)")
