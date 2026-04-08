import pandas as pd
import os

# === File Paths ===
EVENT_FILE = "../data_cleaned/SriLanka_EventCalendar.csv"
OUTPUT_FILE = "../data_cleaned/Event_Month_Tagged.csv"

# === Load Event Calendar ===
df_events = pd.read_csv(EVENT_FILE)

# === Extract active event months ===
active_months = set(df_events["Start Month"].str.capitalize()) | set(df_events["End Month"].str.capitalize())

# === All months list ===
months_order = ["January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December"]

# === Create Tag Data ===
tagged_data = []
for month in months_order:
    tagged_data.append({
        "Month": month,
        "Has_Event": "Yes" if month in active_months else "No"
    })

# === Convert to DataFrame ===
df_tagged = pd.DataFrame(tagged_data)

# === Save CSV ===
os.makedirs("../data_cleaned/", exist_ok=True)
df_tagged.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"✅ Generated Event_Month_Tagged.csv at {OUTPUT_FILE}")
print(df_tagged)
