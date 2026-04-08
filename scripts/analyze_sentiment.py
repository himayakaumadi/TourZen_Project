import os
import sys
import math
from statistics import mean

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

from firebase_admin import db

# Ensure we can import firebase_config from project root (initializes Firebase)
sys.path.append("..")
import firebase_config  # noqa: F401  # side-effect: initializes Firebase app


def ensure_vader():
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon")


def label_from_compound(c):
    """
    Standard VADER thresholds:
      compound >=  0.05 => Positive
      compound <= -0.05 => Negative
      otherwise         => Neutral
    """
    if c >= 0.05:
        return "Positive", 1
    elif c <= -0.05:
        return "Negative", -1
    else:
        return "Neutral", 0


def safe_float(x):
    try:
        if x is None:
            return None
        # Handle strings like "nan"
        if isinstance(x, str) and x.strip().lower() == "nan":
            return None
        v = float(x)
        # Convert NaN to None
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None


def process_category(category: str):
    """
    category: 'attractions' or 'hotels'
    Reads:   /reviews/{category}/{PLACE_ID}/{review_id}
    Writes:  sentiment fields back on each review
             and aggregates at /review_stats/{category}/{PLACE_ID}
    """
    print(f"\n🔎 Processing category: {category}")

    reviews_root = db.reference(f"reviews/{category}")
    stats_root = db.reference(f"review_stats/{category}")

    # Pull whole category once (console can show read-only for large nodes; SDK is fine)
    snapshot = reviews_root.get() or {}
    if not snapshot:
        print(f"⚠ No reviews found under /reviews/{category}")
        return

    sia = SentimentIntensityAnalyzer()
    place_count = 0
    total_updated = 0

    for place_id, reviews in snapshot.items():
        if not isinstance(reviews, dict):
            continue

        pos_cnt = neg_cnt = neu_cnt = 0
        sentiments = []
        ratings = []

        # We'll batch small updates to reduce chatter
        per_place_updates = {}

        for review_id, review in reviews.items():
            if not isinstance(review, dict):
                continue

            text = (review.get("review") or "").strip()
            if not text:
                # If no text, skip sentiment but keep rating for aggregates
                r = safe_float(review.get("rating"))
                if r is not None:
                    ratings.append(r)
                continue

            # Compute VADER sentiment (compound)
            scores = sia.polarity_scores(text)
            compound = scores["compound"]
            label, score = label_from_compound(compound)

            # Count buckets for aggregates
            if label == "Positive":
                pos_cnt += 1
            elif label == "Negative":
                neg_cnt += 1
            else:
                neu_cnt += 1

            sentiments.append(score)

            # Gather rating if present
            r = safe_float(review.get("rating"))
            if r is not None:
                ratings.append(r)

            # Prepare update paths
            per_place_updates[f"{place_id}/{review_id}/sentiment_label"] = label
            per_place_updates[f"{place_id}/{review_id}/sentiment_score"] = score
            per_place_updates[f"{place_id}/{review_id}/sentiment_compound"] = round(compound, 4)

        # Write back all review-level sentiment fields in one go (per place)
        if per_place_updates:
            reviews_root.update(per_place_updates)
            total_updated += len([k for k in per_place_updates.keys() if k.endswith("/sentiment_label")])

        # Compute aggregates
        total_reviews = pos_cnt + neg_cnt + neu_cnt
        avg_sent = round(mean(sentiments), 4) if sentiments else None
        avg_rating = round(mean(ratings), 3) if ratings else None

        stats_root.child(place_id).update({
            "total_reviews": total_reviews,
            "positive_count": pos_cnt,
            "neutral_count": neu_cnt,
            "negative_count": neg_cnt,
            "avg_sentiment_score": avg_sent,
            "avg_rating": avg_rating,
        })

        place_count += 1
        print(f"{category}:{place_id} — reviews={total_reviews}, avg_sent={avg_sent}, avg_rating={avg_rating}")

    print(f"\nDone {category}: places processed={place_count}, reviews updated={total_updated}")


if __name__ == "__main__":
    ensure_vader()
    process_category("attractions")
    process_category("hotels")
    print("\nSentiment analysis complete. Review stats available under /review_stats/")
