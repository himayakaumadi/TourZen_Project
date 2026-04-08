import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import os

# === Firebase Initialization ===
if not firebase_admin._apps:
    cred = credentials.Certificate("../tourzen-firebase-adminsdk.json")  # Adjust path if needed
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://tourzen-2ab15-default-rtdb.asia-southeast1.firebasedatabase.app"
    })

# === File paths ===
BASE_PATH = "../data_cleaned/"
FILES = {
    "weather": "Province_WeatherMonthly.csv",
    "events": "SriLanka_EventCalendar.csv",
    "event_month_tags": "Event_Month_Tagged.csv"
}

# === Upload CSV to Firebase ===
def upload_csv(node_name, csv_file):
    print(f"📤 Uploading {csv_file} into {node_name}/ ...")
    df = pd.read_csv(BASE_PATH + csv_file)
    ref = db.reference(node_name)
    ref.set({})  # Optional: Clear previous data

    for i, row in df.iterrows():
        ref.push(row.to_dict())

    print(f"✅ Uploaded {len(df)} records into {node_name}/")

# === Run Uploads ===
for node, filename in FILES.items():
    upload_csv(node, filename)

print("🎉 All datasets uploaded successfully to Firebase!")
