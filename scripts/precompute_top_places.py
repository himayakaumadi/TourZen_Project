import os
import sys
from firebase_admin import db

# ★ Add project root so firebase_config is found
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(PROJECT_ROOT)

import firebase_config  # initializes Firebase


def load_stats(category):
    ref = db.reference(f"review_stats/{category}")
    return ref.get() or {}


def load_sample_review(category, place_id):
    ref = db.reference(f"reviews/{category}/{place_id}")
    snap = ref.order_by_key().limit_to_first(1).get() or {}
    for _, v in snap.items():
        return v
    return {}


def compute_top10(category):
    stats = load_stats(category)
    province_map = {}

    for place_id, s in stats.items():
        sample = load_sample_review(category, place_id)
        province = (sample.get("province") or "Unknown").strip()

        entry = {
            "place_id": place_id,
            "name": sample.get("name", ""),
            "district": sample.get("district", ""),
            "province": province,
            "photo_url": sample.get("photo_url"),
            "avg_sentiment": s.get("avg_sentiment_score", 0),
            "total_reviews": s.get("total_reviews", 0),
            "avg_rating": s.get("avg_rating"),
        }

        province_map.setdefault(province, []).append(entry)

    # Sort & keep Top 10
    for prov, items in province_map.items():
        items.sort(
            key=lambda x: (x["avg_sentiment"], x["total_reviews"], x["avg_rating"] or 0),
            reverse=True
        )
        province_map[prov] = items[:10]

    return province_map


def upload_cached(category, data):
    base = f"cached/top10/{category}"
    ref = db.reference(base)
    ref.delete()
    ref.set(data)
    print(f"✔ Uploaded: {base}")


def main():
    print("⏳ Computing Top 10 Attractions…")
    att = compute_top10("attractions")
    upload_cached("attractions", att)

    print("⏳ Computing Top 10 Hotels…")
    hotels = compute_top10("hotels")
    upload_cached("hotels", hotels)

    print("🎉 Cached top-ten lists uploaded successfully!")


if __name__ == "__main__":
    main()
