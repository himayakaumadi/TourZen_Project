# routes/place_routes.py
from flask import Blueprint, render_template, abort
import sys
sys.path.append("..")
import firebase_config
from firebase_admin import db
from dotenv import load_dotenv
load_dotenv()
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- ELEGANT CURATED CONTENT (Handcrafted for Top Icons) ---
ELEGANT_PLACE_CONTENT = {
    "sigiriya": "The legendary 'Lion Rock' fortress, a UNESCO World Heritage site featuring ancient frescoes, mirror walls, and breathtaking terraced gardens atop a massive granite monolith. This 5th-century citadel is a masterpiece of ancient urban planning and engineering.",
    "tooth relic": "Sri Lanka's most sacred Buddhist shrine, housing the sacred tooth relic of the Buddha. Located in the heart of Kandy, the temple features golden canopies, intricate Kandyan architecture, and a profound spiritual atmosphere that draws pilgrims from across the globe.",
    "horton plains": "A hauntingly beautiful highland plateau featuring the dramatic 'World's End' sheer precipice and the mist-shrouded Baker's Falls. This mystical landscape is home to unique flora and fauna found nowhere else on Earth.",
    "galle fort": "A living historical masterpiece where 17th-century Dutch colonial architecture meets the vibrant azure waters of the Indian Ocean. Walk along the monolithic ramparts and explore narrow cobblestone streets filled with boutique cafes and history.",
    "nine arch": "An architectural marvel hidden in the lush emerald hills of Ella. This stunning colonial-era railway bridge, built entirely without steel, spans a deep jungle ravine and offers one of the most iconic views in Sri Lanka.",
    "yala": "A wild sanctuary of untamed beauty, home to the world's highest density of leopards. This coastal forest offers thrilling safaris where you can witness wandering elephants, sloth bears, and exotic tropical birds in their natural habitat.",
    "pinnawala": "A heart-warming sanctuary where orphaned elephants roam freely. The sight of these gentle giants bathing in the Ma Oya River is a truly unforgettable experience that highlights Sri Lanka's deep connection with wildlife.",
    "nuwara eliya": "Often called 'Little England,' this misty highland retreat is famous for its rolling tea estates, colonial-era bungalows, and the beautiful Lake Gregory. It is the heart of Sri Lanka's tea country.",
    "kandy lake": "A serene, man-made lake at the heart of the hill capital, built by the last king of Kandy. A walk around its perimeter offers peaceful views of the Temple of the Tooth and the surrounding mist-covered mountains.",
    "knuckles": "A rugged mountain range named for its resemblance to a clenched fist. This UNESCO World Heritage site is a hiker's paradise, featuring hidden waterfalls, crystal-clear streams, and ancient 'cloud forests'.",
    "gregory lake": "The centerpiece of Nuwara Eliya, this historic lake offers a variety of recreational activities, from boat rides to jet skiing, all set against a backdrop of crisp mountain air and colonial charm.",
    "botanical garden": "One of the finest botanical gardens in Asia, spanning 147 acres and featuring over 4,000 species of plants. Highlights include the towering orchid house and the iconic avenue of royal palms.",
    "polonnaruwa": "The medieval capital of Sri Lanka, showcasing incredibly well-preserved ruins of ancient palaces, monasteries, and the giant reclining Buddha statues of Gal Vihara.",
    "dambulla": "An ancient cave temple complex adorned with over 150 stunning Buddha statues and vibrant religious murals that have survived for over 2,000 years in a massive rock outcrop.",
    "cinemmon citadel": "A premium riverfront hotel in Kandy that blends traditional Kandyan themes with modern luxury, offering breathtaking views of the Mahaweli River and the surrounding lush hills."
}

def get_smart_description(name, category, district, original_desc):
    """
    Ensures 'All Places' have a professional description by using 
    curated text, database info, or a smart generated fallback.
    """
    name_lower = (name or "").lower()
    
    # 1. Try Curated "Elegant" Content first
    for key, text in ELEGANT_PLACE_CONTENT.items():
        if key in name_lower:
            return text
            
    # 2. Use Database Description if it's high quality (more than a few words)
    if original_desc and len(original_desc) > 30:
        return original_desc
        
    # 3. SMART FALLBACK: If nothing exists, generate a professional template
    if category == "hotels":
        return f"Experience premium hospitality at {name or 'this premier hotel'}. Located in the beautiful {district or 'serene area'} of Sri Lanka, this destination offers a perfect blend of comfort and local charm, highly recommended for travelers seeking a memorable stay."
    else:
        return f"Explore the wonders of {name or 'this unique attraction'} in {district or 'Sri Lanka'}. This popular destination showcases the natural beauty and cultural heritage of the region, offering an immersive experience that captures the true essence of Sri Lankan tourism."

place_bp = Blueprint("place_bp", __name__, url_prefix="/place")

VALID_CATEGORIES = {"attractions", "hotels"}

@place_bp.route("/<category>/<place_id>")
def place_detail(category, place_id):

    if category not in VALID_CATEGORIES:
        abort(404)

    # ---------------------------------------------------
    # 1) READ AGGREGATED STATS (correct structure)
    # review_stats/<category>/<place_id>
    # ---------------------------------------------------
    stats_ref = db.reference(f"review_stats/{category}/{place_id}")
    stats = stats_ref.get() or {}

    # ---------------------------------------------------
    # 2) READ RAW REVIEWS LIST
    # reviews/<category>/<place_id>
    # ---------------------------------------------------
    reviews_ref = db.reference(f"reviews/{category}/{place_id}")
    reviews = reviews_ref.get() or {}

    # ---------------------------------------------------
    # Extract first review as meta
    # ---------------------------------------------------
    meta = {}
    for _, r in reviews.items():
        if isinstance(r, dict):
            meta = r
            break

    # ------------------------------
    # Extract main place attributes (With Smart Description Resolver)
    # ------------------------------
    name = meta.get("name") or "Unknown"
    address = meta.get("address") or ""
    district = meta.get("district") or ""
    province = meta.get("province") or ""
    
    raw_desc = meta.get("description") or meta.get("wiki_summary") or ""
    description = get_smart_description(name, category, district, raw_desc)

    # ------------------------------
    # Photo URL
    # ------------------------------
    raw_photo = meta.get("photo_url") or ""
    photo_url = ""

    # If this is a Google Place Photo URL, append API key
    # Use our secure Google Photo Proxy instead of leaking the API key via direct links
    if place_id:
        photo_url = f"/api/photo_proxy/{place_id}"
    else:
        photo_url = raw_photo or ""

    # Some entries use lat/lng — others use latitude/longitude
    lat = meta.get("lat") or meta.get("latitude")
    lng = meta.get("lng") or meta.get("longitude")

    # ------------------------------
    # Google Map embed
    # ------------------------------
    if lat and lng:
        map_src = f"https://maps.google.com/maps?q={lat},{lng}&z=15&output=embed"
    else:
        query = f"{name} {district or province}".replace(" ", "+")
        map_src = f"https://maps.google.com/maps?q={query}&z=15&output=embed"

    # ------------------------------
    # Latest 5 reviews
    # ------------------------------
    recent_reviews = []
    for rid, r in list(reviews.items())[:5]:
        if isinstance(r, dict):
            recent_reviews.append({
                "author": r.get("author") or r.get("user") or "Anonymous",
                "rating": r.get("rating"),
                "text": r.get("review") or r.get("text") or "",
                "sentiment": r.get("sentiment_label"),
                "compound": r.get("sentiment_compound")
            })

    context = {
        "category": category,
        "place_id": place_id,

        "name": name,
        "address": address,
        "district": district,
        "province": province,
        "description": description,

        "photo_url": photo_url,
        "avg_rating": stats.get("avg_rating"),
        "avg_sentiment": stats.get("avg_sentiment_score"),
        "total_reviews": stats.get("total_reviews", 0),

        "map_src": map_src,
        "recent_reviews": recent_reviews
    }

    return render_template("place_detail.html", **context)
