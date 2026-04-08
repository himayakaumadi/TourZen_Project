import os
import requests
from flask import Blueprint, redirect, url_for

# Blueprint for fetching and proxying Google Place photos securely
photo_bp = Blueprint("photo_bp", __name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

@photo_bp.route("/api/photo_proxy/<place_id>")
def photo_proxy(place_id):
    """
    Takes a Google Place ID, fetches the best photo reference, 
    and redirects the browser to the high-quality Google Photo URL.
    """
    if not GOOGLE_API_KEY:
        # Fallback to a nice local image if API key is missing
        return redirect(url_for('static', filename='images/unawatuna.png'))
    
    try:
        # 1. Fetch Place Details (requesting ONLY the 'photos' field to minimize costs)
        details_url = (
            f"https://maps.googleapis.com/maps/api/place/details/json"
            f"?place_id={place_id}&fields=photos&key={GOOGLE_API_KEY}"
        )
        response = requests.get(details_url, timeout=5).json()
        
        # 2. Extract the first photo reference
        photos = response.get("result", {}).get("photos", [])
        if not photos:
            # Fallback if no photos exist for this place
            return redirect(url_for('static', filename='images/unawatuna.png'))
            
        photo_ref = photos[0].get("photo_reference")
        
        # 3. Construct the official Google Photo URL
        # maxwidth=600 is plenty for the dashboard thumbnails
        final_photo_url = (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth=600&photoreference={photo_ref}&key={GOOGLE_API_KEY}"
        )
        
        # 4. Redirect the client's browser to the actual image
        return redirect(final_photo_url)

    except Exception as e:
        print(f"⚠ Photo Proxy Error for {place_id}: {e}")
        return redirect(url_for('static', filename='images/unawatuna.png'))
