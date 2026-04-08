import pandas as pd
from firebase_admin import db
import os
import sys

# ✅ Ensure Firebase config is loaded
sys.path.append("..")
import firebase_config  # This initializes Firebase once

# === File paths ===
ATTRACTIONS_REVIEWS_FILE = "../data_unstructured/attractions_reviews.csv"
HOTELS_REVIEWS_FILE = "../data_unstructured/hotels_reviews.csv"

def upload_reviews(csv_file, node_name):
    print(f"🚀 Uploading reviews from {csv_file} to Firebase node: /reviews/{node_name}/")

    df = pd.read_csv(csv_file)

    # ✅ Group by Place_ID so structure stays clean in Firebase
    grouped = df.groupby("Place_ID")

    reviews_ref = db.reference(f"reviews/{node_name}")
    # reviews_ref.set({})  # Optional: Uncomment to clear previous data

    upload_count = 0

    for place_id, group in grouped:
        place_ref = reviews_ref.child(place_id)

        for _, row in group.iterrows():
            review_data = {
                "name": row["Name"],
                "province": row["Province"],
                "district": row["District"],
                "author": row["Review_Author"],
                "rating": row["Rating"],
                "review": row["User_Review"],
                "photo_url": row["Photo_URL"]
            }

            # ✅ Fix: Replace NaN with None to avoid Firebase JSON errors
            cleaned_data = {
                key: (None if pd.isna(value) or str(value).lower() == "nan" else value)
                for key, value in review_data.items()
            }

            place_ref.push(cleaned_data)
            upload_count += 1

    print(f"✅ Uploaded {upload_count} reviews under /reviews/{node_name}/")

if __name__ == "__main__":
    # ✅ Upload Attractions Reviews
    if os.path.exists(ATTRACTIONS_REVIEWS_FILE):
        upload_reviews(ATTRACTIONS_REVIEWS_FILE, "attractions")
    else:
        print("⚠ No attractions review file found.")

    # ✅ Upload Hotel Reviews
    if os.path.exists(HOTELS_REVIEWS_FILE):
        upload_reviews(HOTELS_REVIEWS_FILE, "hotels")
    else:
        print("⚠ No hotels review file found.")

    print("🎉 ALL REVIEWS UPLOADED TO FIREBASE SUCCESSFULLY ✅")
