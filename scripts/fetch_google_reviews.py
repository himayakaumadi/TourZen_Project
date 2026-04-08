import os
import csv
import requests
import pandas as pd
from dotenv import load_dotenv

# ✅ Load API Key from .env
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# ✅ File paths
ATTRACTIONS_FILE = "../data_raw/attractions_master.csv"
HOTELS_FILE = "../data_raw/hotels_master.csv"
OUTPUT_ATTRACTIONS = "../data_unstructured/attractions_reviews.csv"
OUTPUT_HOTELS = "../data_unstructured/hotels_reviews.csv"

# ✅ Firebase / Dashboard Structured Output Fields
FIELDS = ["Name", "Type", "Province", "District", "Review_Author", "Rating", "User_Review", "Photo_URL", "Place_ID"]

# ✅ Ensure output directory exists
os.makedirs("../data_unstructured/", exist_ok=True)

def fetch_place_id(search_query):
    """Fetch place_id using Google Places Text Search API"""
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={search_query}&key={API_KEY}"
    res = requests.get(url).json()

    if res.get("results"):
        place = res["results"][0]
        return place.get("place_id"), place.get("photos", [{}])[0].get("photo_reference", None)
    return None, None

def fetch_reviews(place_id):
    """Fetch place reviews using Google Place Details API"""
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=review,rating,photo,user_ratings_total&key={API_KEY}"
    res = requests.get(url).json()

    reviews_data = []
    if res.get("result", {}).get("reviews"):
        for review in res["result"]["reviews"]:
            reviews_data.append({
                "author": review.get("author_name", "N/A"),
                "rating": review.get("rating", "N/A"),
                "text": review.get("text", "No review text")
            })
    return reviews_data

def generate_photo_url(photo_ref):
    """Generate public photo URL from photo reference"""
    if photo_ref:
        return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={API_KEY}"
    return None

def process_file(input_csv, output_csv, content_type):
    df = pd.read_csv(input_csv)
    all_data = []

    for _, row in df.iterrows():
        name = row["Name"]
        province = row["Province"]
        district = row["District"]
        search_key = row["Google_Search_Keyword"]

        print(f"🔍 Searching: {name} ...")
        place_id, photo_ref = fetch_place_id(search_key)

        if not place_id:
            print(f"❌ Place ID not found for {name}")
            continue

        print(f"✅ Place ID Found: {place_id}")
        photo_url = generate_photo_url(photo_ref)

        # Fetch reviews
        reviews = fetch_reviews(place_id)
        for review in reviews:
            all_data.append({
                "Name": name,
                "Type": content_type,
                "Province": province,
                "District": district,
                "Review_Author": review["author"],
                "Rating": review["rating"],
                "User_Review": review["text"],
                "Photo_URL": photo_url,
                "Place_ID": place_id
            })

    # ✅ Save to CSV
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_data)

    print(f"🎉 Saved data to {output_csv} — Total reviews: {len(all_data)}")

# ✅ Run for both categories
print("\n🚀 Fetching ATTRACTIONS reviews...")
process_file(ATTRACTIONS_FILE, OUTPUT_ATTRACTIONS, "Attraction")

print("\n🚀 Fetching HOTELS reviews...")
process_file(HOTELS_FILE, OUTPUT_HOTELS, "Hotel")

print("\n✅ ALL DONE — Reviews + Ratings + Photos collected!")
