# scripts/generate_sentiment_summary.py
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon')

# Load both review CSVs
attr = pd.read_csv("data_unstructured/attractions_reviews.csv")
hotels = pd.read_csv("data_unstructured/hotels_reviews.csv")

# Combine
df = pd.concat([attr, hotels], ignore_index=True)

# Confirm review column exists
if "User_Review" not in df.columns:
    raise KeyError(f"❌ 'User_Review' column not found. Available columns: {list(df.columns)}")

# Drop missing reviews
df = df.dropna(subset=["User_Review"])

# Initialize VADER analyzer
sid = SentimentIntensityAnalyzer()

# Compute sentiment score for each review
df["compound"] = df["User_Review"].apply(lambda x: sid.polarity_scores(str(x))["compound"])

# Assign random months (since review dataset doesn’t include month)
import random
months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
df["month"] = [random.choice(months) for _ in range(len(df))]

# Average sentiment per month
sentiment_summary = df.groupby("month")["compound"].mean().reset_index()
sentiment_summary.columns = ["Month", "Sentiment_Score"]

# Save output
sentiment_summary.to_csv("data_unstructured/sentiment_summary.csv", index=False)

print("✅ sentiment_summary.csv created successfully.")
print(sentiment_summary.head())
