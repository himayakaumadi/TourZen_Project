import requests
import pandas as pd
import time
from flask import Blueprint
from dotenv import load_dotenv
import os
from firebase_config import firebase_db as db

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

review_bp = Blueprint('review_bp', __name__)

sri_lanka_places = {
    "Sigiriya Rock Fortress": "ChIJ9Sm5as4A_zoRjJwBv7XGxG8",
    "Temple of the Tooth, Kandy": "ChIJgXnH4Y8D_zoR8UdQuZnMqoo",
    "Galle Fort": "ChIJk5wE7UqT_zoRZ1VmvbCjvJQ",
    "Shangri-La Colombo": "ChIJM6OIBZTA_zoRKeWZ8pVfU4A"
}

@review_bp.route("/load_reviews")
def load_reviews():
    all_reviews = []
    for name, pid in sri_lanka_places.items():
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={pid}&fields=name,rating,review&key={API_KEY}"
        res = requests.get(url).json()
        if "result" in res and "reviews" in res["result"]:
            for r in res["result"]["reviews"]:
                review_data = {
                    "place": name,
                    "rating": r.get("rating"),
                    "review_text": r.get("text"),
                    "time": r.get("relative_time_description")
                }
                all_reviews.append(review_data)
                db.reference("reviews").push(review_data)
        time.sleep(1)
    if all_reviews:
        df = pd.DataFrame(all_reviews)
        df.to_csv("sri_lanka_reviews.csv", index=False)
        return f"✅ Loaded {len(df)} reviews and saved to sri_lanka_reviews.csv"
    return "No reviews found."
