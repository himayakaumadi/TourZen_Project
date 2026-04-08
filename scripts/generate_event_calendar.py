import pandas as pd
import os

# === Output path for cleaned event calendar ===
OUTPUT_FILE = "../data_cleaned/SriLankaEventCalendar.csv"

# === Event dataset definition ===
events = [
    {"Event": "Kandy Esala Perahera", "Category": "Cultural Festival", "Locations": "Kandy", "Start Month": "August", "End Month": "August", "Impact": "High"},
    {"Event": "Vesak Festival", "Category": "Buddhist Religious", "Locations": "Nationwide", "Start Month": "May", "End Month": "May", "Impact": "High"},
    {"Event": "Poson Pilgrimage", "Category": "Religious Pilgrimage", "Locations": "Anuradhapura, Mihintale", "Start Month": "June", "End Month": "June", "Impact": "High"},
    {"Event": "Sinhala & Tamil New Year", "Category": "National Festival", "Locations": "Nationwide", "Start Month": "April", "End Month": "April", "Impact": "Medium"},
    {"Event": "Christmas & New Year Tourism Season", "Category": "Seasonal Tourism", "Locations": "Colombo, Galle, Coastal Belt", "Start Month": "December", "End Month": "January", "Impact": "High"},
    {"Event": "Whale Watching Season", "Category": "Wildlife Tourism", "Locations": "Mirissa, Trincomalee", "Start Month": "November", "End Month": "March", "Impact": "Medium"},
    {"Event": "Adam’s Peak Pilgrimage Season", "Category": "Pilgrimage Trekking", "Locations": "Sri Pada Peak", "Start Month": "December", "End Month": "May", "Impact": "Medium"},
    {"Event": "Kataragama Festival", "Category": "Religious Festival", "Locations": "Kataragama", "Start Month": "July", "End Month": "August", "Impact": "Medium"},
    {"Event": "Arugam Bay Surfing Season", "Category": "Adventure Tourism", "Locations": "Arugam Bay", "Start Month": "April", "End Month": "October", "Impact": "Medium"},
    {"Event": "Galle Literary Festival", "Category": "Cultural Event", "Locations": "Galle", "Start Month": "January", "End Month": "January", "Impact": "Medium"},
    {"Event": "Nallur Kovil Festival", "Category": "Hindu Cultural", "Locations": "Jaffna", "Start Month": "August", "End Month": "September", "Impact": "Medium"},
    {"Event": "Deepavali Festival", "Category": "Hindu Cultural", "Locations": "Colombo, Jaffna, Batticaloa", "Start Month": "October", "End Month": "November", "Impact": "Medium"}
]

# === Convert to DataFrame ===
df_events = pd.DataFrame(events)

# === Ensure /data_cleaned/ exists ===
os.makedirs("../data_cleaned/", exist_ok=True)

# === Save CSV ===
df_events.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"✅ Event calendar dataset generated: {OUTPUT_FILE}")
print(df_events.head())
