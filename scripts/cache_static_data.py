import os
import sys
import pandas as pd
from firebase_admin import db

# ★ Add project root so firebase_config is found
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)
import firebase_config

BASE = os.path.join(os.path.dirname(__file__), "..", "data_cleaned")

WEATHER_FILE = os.path.join(BASE, "Province_WeatherMonthly.csv")
EVENT_FILE = os.path.join(BASE, "SriLanka_EventCalendar.csv")
FORECAST_FILE = os.path.join(BASE, "forecast_future_ensemble_prophet.csv")

def upload(path, data):
    ref = db.reference(path)
    ref.delete()
    ref.set(data)
    print(f"✔ Uploaded {path}")

def main():
    print("⏳ Caching weather...")
    weather = pd.read_csv(WEATHER_FILE).to_dict(orient="records")
    upload("cache_static/weather", weather)

    print("⏳ Caching events...")
    events = pd.read_csv(EVENT_FILE).to_dict(orient="records")
    upload("cache_static/events", events)

    print("⏳ Caching forecast...")
    fc = pd.read_csv(FORECAST_FILE).to_dict(orient="records")
    upload("cache_static/forecast", fc)

    print("🎉 All static datasets cached successfully!")

if __name__ == "__main__":
    main()
