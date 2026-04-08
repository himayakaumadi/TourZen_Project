import os
import requests
import pandas as pd
from flask import Blueprint, render_template, session, redirect, url_for
import urllib.parse

event_bp = Blueprint("event_bp", __name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_CLEANED = os.path.join(PROJECT_ROOT, "data_cleaned")
EVENT_FILE = os.path.join(DATA_CLEANED, "SriLanka_EventCalendar_CLEANED.csv")

# Load Event CSV once
EVENT_DF = None
if os.path.exists(EVENT_FILE):
    try:
        EVENT_DF = pd.read_csv(EVENT_FILE)
        EVENT_DF.columns = [c.strip() for c in EVENT_DF.columns]
    except Exception as e:
        print("Failed to load Event CSV:", e)

def get_event_csv_data(event_name):
    if EVENT_DF is None:
        return None
    
    # Try exact match or case-insensitive match
    for _, row in EVENT_DF.iterrows():
        ev_name = str(row.get("Event", "")).strip()
        if ev_name.lower() == event_name.lower():
            return {
                "Event": ev_name,
                "Category": str(row.get("Category", "Event")),
                "Locations": str(row.get("Locations", "Sri Lanka")),
                "Start Month": str(row.get("Start_Month", "")).capitalize(),
                "End Month": str(row.get("End_Month", "")).capitalize(),
                "Impact": str(row.get("Impact", "Medium"))
            }
    return None

# Elegant Curated Content mapping for rich descriptions and high-quality hero imagery
ELEGANT_EVENT_CONTENT = {
    "Kandy Esala Perahera": {
        "description": "Experience the Kandy Esala Perahera, an extraordinary cultural spectacle and one of the oldest and grandest of all Buddhist festivals in Sri Lanka. Witness a mesmerizing procession featuring elegantly adorned elephants, captivating fire-dancers, traditional Kandyan drummers, and whip-crackers under the warm tropical night sky. A deeply spiritual journey culminating at the legendary Temple of the Tooth Relic.",
        "image_file": "KandyEsalaPerahera.jpeg"
    },
    "Vesak Festival": {
        "description": "Vesak is the most luminous and spiritual time of the year, celebrating the birth, enlightenment, and passing away of Lord Buddha. Nationwide, streets blossom with intricately crafted, glowing lanterns (Vesak koodu) and spectacular illuminated pandals. Kindness radiates as locals offer free food and drinks at 'Dansalas', creating an atmosphere of deep harmony, breathtaking light, and absolute peace.",
        "image_file": "VesakFestival.jpeg"
    },
    "Sinhala & Tamil New Year": {
        "description": "Welcome to the joyous Sinhala and Tamil New Year (Avurudu), a massive nationwide celebration marking the astrological transition of the sun. Deeply rooted in indigenous agricultural traditions, families dress in vibrant auspicious colors, partake in community games, and prepare tables full of traditional milk-rice (Kiribath) and sweetmeats. An unforgettable, lively immersion into authentic Sri Lankan hospitality and family heritage.",
        "image_file": "Sinhala&TamilNewYear.jpeg"
    },
    "Poson Pilgrimage": {
        "description": "Poson Poya commemorates the profound arrival of Buddhism in Sri Lanka. The ancient centers of Anuradhapura and Mihintale transform into breathtaking hubs of devotion, illuminated by thousands of oil lamps. Join streams of pilgrims draped in white silk climbing the historic stairway of Mihintale, seeking spiritual solace in an incredibly moving, serene display of religious dedication.",
        "image_file": "PosonPilgrimage.jpeg"
    },
    "Christmas & New Year Tourism Season": {
        "description": "As December breezes cool the paradise island, Sri Lanka dazzles with a unique tropical Christmas. Historic colonial cities like Colombo and Galle light up in festive splendor, offering world-class dining, bustling night markets, and exclusive seasonal retreats along the Southern Coastal Belt. Celebrate the New Year watching spectacular fireworks over the Indian Ocean with unparalleled luxury.",
        "image_file": "Christmas.jpeg"
    },
    "Whale Watching Season": {
        "description": "Set sail into the deep blue Indian Ocean for an unparalleled marine wildlife encounter. Sri Lanka's southern and eastern coasts become globally renowned hotspots for spotting majestic Blue Whales, acrobat Spinner Dolphins, and elusive Sperm whales migrating across the warm currents. A thrilling, once-in-a-lifetime eco-tourism adventure.",
        "image_file": "WhaleWatching.jpeg"
    },
    "Adams Peak Pilgrimage Season": {
        "description": "Embark on the legendary midnight ascent of Adam's Peak (Sri Pada). This sacred mountain unites diverse faiths, culminating in an awe-inspiring sunrise where the peak casts a perfect triangular shadow across the central highlands. Walking alongside chanting pilgrims under a blanket of stars to reach the sacred footprint at the summit is profoundly inspiring.",
        "image_file": "AdamsPeak.jpeg"
    },
    "Kataragama Festival": {
        "description": "Immerse yourself in the intense spiritual energy of the Kataragama Festival, an extraordinary multi-religious gathering dedicated to the warrior deity Skanda. Witness breathtaking acts of devotion, from hypnotic kavadi dances and fire-walking to rhythmic drumming echoing through the jungles. An unparalleled cultural phenomenon showcasing raw faith and mystique.",
        "image_file": "KataragamaFestival.jpeg"
    },
    "Arugam Bay Surfing Season": {
        "description": "Ride the legendary swells of Arugam Bay, globally recognized as one of the top surf destinations on the planet. From April to October, perfect right-hand point breaks invite surfers of all levels. Relax in the laid-back, bohemian seaside village offering vibrant nightlife, yoga retreats, and endless golden sunshine on the exotic East Coast.",
        "image_file": "ArugambaySurfing.jpeg"
    },
    "Galle Literary Festival": {
        "description": "Within the cobblestone streets of the UNESCO World Heritage Galle Fort, this celebrated international festival gathers brilliant literary minds, celebrated authors, and intellectuals. Enjoy intimate poetry readings, profound debates, and elegant curated dinners inside stunning Dutch-colonial architecture. A refined cultural oasis for the sophisticated traveler.",
        "image_file": "GalleLiterary.jpeg"
    },
    "Nallur Kovil Festival": {
        "description": "Experience the grandest and longest Hindu festival in Sri Lanka at the spectacular Nallur Kandaswamy Kovil in Jaffna. Over twenty-five days of sheer grandeur, heavily adorned deities are paraded on magnificent golden chariots amidst thousands of devotees, classical musicians, and vibrant temple artistry. A profound testament to Northern Tamil culture.",
        "image_file": "NallurKovil.jpeg"
    },
    "Deepavali Festival": {
        "description": "Deepavali, the beautiful Festival of Lights, celebrates the spiritual triumph of light over darkness. Nationwide, Hindu homes and temples are intricately adorned with mesmerizing oil lamps, colorful kolam art, and vibrant floral garlands, paired with the joyful exchange of traditional sweets and spectacular firework displays lighting the evening skies.",
        "image_file": "Deepavali.jpeg"
    },
    "Vel Festival": {
        "description": "Colombo's most vibrant Hindu street festival, dedicated to the God of War, Lord Murugan. The entire city resounds with the beating of traditional drums and joyous chants as the magnificent, heavily decorated silver chariot makes its way through bustling streets. An extraordinary, colorful display of devotion amid a modern metropolis.",
        "image_file": "VelFestival.jpeg"
    },
    "Maha Shivarathri": {
        "description": "A deeply contemplative and powerful Hindu night dedicated to Lord Shiva. Temples overflow with continuous chanting, rhythmic prayers, and offerings of milk and bilva leaves well into the dawn. A powerful, transcendent cultural experience observing the intense spiritual stamina and dedication of the Hindu community.",
        "image_file": "Mahashivarathri.jpeg"
    },
    "Thai Pongal": {
        "description": "Celebrate the joyous, deeply traditional Tamil harvest festival of Thai Pongal. As the sun rises over breathtaking landscapes, families gather to boil newly harvested rice with rich jaggery and fresh milk in beautifully decorated clay pots until it overflows—symbolizing incoming prosperity and boundless joy. A vibrant, welcoming display of agricultural reverence.",
        "image_file": "ThaiPongal.jpeg"
    }
}

@event_bp.route("/event/<path:event_name>")
def event_detail(event_name):
    if "user" not in session:
        return redirect(url_for("auth_bp.login"))
        
    event_name_decoded = urllib.parse.unquote(event_name)
    
    # 1. Fetch Local CSV Data
    csv_data = get_event_csv_data(event_name_decoded)
    
    # Fallback default values if not in CSV
    if not csv_data:
        csv_data = {
            "Event": event_name_decoded,
            "Category": "Special Event",
            "Locations": "Sri Lanka",
            "Start Month": "",
            "End Month": "",
            "Impact": "Medium"
        }
        
    # 2. Extract Premium Curated Data First
    curated_data = ELEGANT_EVENT_CONTENT.get(event_name_decoded, {})
    
    # Merge datasets
    description = curated_data.get("description", "")
    image_file = curated_data.get("image_file", "unawatuna.png")
    image_url = url_for('static', filename=f'images/{image_file}')
    
    # Generic description fallback if missing from curated map
    if not description:
        description = f"Join us to experience {csv_data['Event']}, a spectacular {csv_data['Category']} celebration deeply rooted in Sri Lankan culture. " \
                      f"Primarily observed across {csv_data['Locations']}, this event drives strong engagement with a '{csv_data['Impact']}' tourism impact rating. " \
                      f"Plan your visit ahead to partake in authentic local traditions."

    # Render template with merged payload
    return render_template(
        "event_detail.html", 
        username=session["user"],
        event_name=csv_data["Event"],
        category=csv_data["Category"],
        locations=csv_data["Locations"],
        start_month=csv_data["Start Month"],
        end_month=csv_data["End Month"],
        impact=csv_data["Impact"],
        description=description,
        image_url=image_url
    )
