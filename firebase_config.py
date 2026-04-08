import firebase_admin
from firebase_admin import credentials, db
import os

# --- USE ABSOLUTE PATH TO PREVENT STARTUP ERRORS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "tourzen-firebase-adminsdk.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://tourzen-2ab15-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

firebase_db = db
