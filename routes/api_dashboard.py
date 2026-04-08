# routes/api_dashboard.py
from flask import Blueprint, request, jsonify
import os
import sys
import pandas as pd
from datetime import datetime
from functools import lru_cache
from collections import defaultdict
import threading
import concurrent.futures
import logging

# try to import firebase_config (optional)
# --- ROBUST FIREBASE INITIALIZATION ---
try:
    # Ensure current directory is in path for imports
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    PROJECT_ROOT = parent_dir

    import firebase_config  # noqa: F401
    from firebase_admin import db
    HAS_FIREBASE = True
except Exception as e:
    HAS_FIREBASE = False
    # Still import logging for lower-level handling
    import logging
    logger = logging.getLogger("api_dashboard")
    logger.error("Firebase connection failed: %s", e)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

from .prediction_logic import predict_monthly

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")

# ---- Local files ----
DATA_CLEANED = os.path.join(PROJECT_ROOT, "data_cleaned")
WEATHER_FILE = os.path.join(DATA_CLEANED, "Province_WeatherMonthly.csv")
EVENT_FILE = os.path.join(DATA_CLEANED, "SriLanka_EventCalendar_CLEANED.csv")  # cleaned CSV expected

# ---- Constants ----
MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
MONTH2NUM = {m: i+1 for i, m in enumerate(MONTHS)}
REGION_TO_PROVINCE = {
    "colombo": "Western", "negombo": "Western", "kalutara": "Western", "gampaha": "Western", "western": "Western",
    "kandy": "Central", "nuwara eliya": "Central", "matale": "Central", "central": "Central",
    "galle": "Southern", "matara": "Southern", "hambantota": "Southern", "southern": "Southern",
    "jaffna": "Northern", "mannar": "Northern", "vavuniya": "Northern", "mullaitivu": "Northern", "kilinochchi": "Northern", "northern": "Northern",
    "trincomalee": "Eastern", "batticaloa": "Eastern", "ampara": "Eastern", "eastern": "Eastern",
    "kurunegala": "North Western", "puttalam": "North Western", "north western": "North Western",
    "anuradhapura": "North Central", "polonnaruwa": "North Central", "north central": "North Central",
    "badulla": "Uva", "monaragala": "Uva", "uva": "Uva",
    "ratnapura": "Sabaragamuwa", "kegalle": "Sabaragamuwa", "sabaragamuwa": "Sabaragamuwa",
}

# --- GLOBAL METADATA CACHE (Speeds up repeated dashboard searches) ---
PLACE_METADATA_CACHE = {
    # Attractions
    "sigiriya": "Central", "tooth relic": "Central", "horton plains": "Central", 
    "ella": "Uva", "nine arch": "Uva", "galle fort": "Southern", "unawatuna": "Southern",
    "yala": "Southern", "minneriya": "North Central", "adams peak": "Central",
    "sri pada": "Central", "polonnaruwa": "North Central", "dambulla": "Central",
    "arugam bay": "Eastern", "pinnawala": "Sabaragamuwa", "nuwara eliya": "Central",
    # Hotels
    "cinnamon citadel": "Central", "ceylon tea trails": "Central",
    "jetwing st. andrew": "Central", "heritance tea factory": "Central",
    "amari galle": "Southern", "heritance ahungalla": "Southern",
    "jetwing lighthouse": "Southern", "shangri-la colombo": "Western",
    "cinnamon grand": "Western"
}

# ---- Logging ----
logger = logging.getLogger("api_dashboard")
logger.setLevel(logging.INFO)

# ---- Preload CSVs once (safe fallbacks) ----
WEATHER_DF = None
EVENT_DF = None
EVENT_INDEX = None  # dict: province -> list(rows)

def _safe_read_csv(path, **kwargs):
    try:
        return pd.read_csv(path, **kwargs)
    except Exception as e:
        logger.warning("Could not read CSV %s: %s", path, e)
        return None

if os.path.exists(WEATHER_FILE):
    WEATHER_DF = _safe_read_csv(WEATHER_FILE, dtype=str)
    if WEATHER_DF is not None:
        # Normalize
        WEATHER_DF.columns = [c.strip() for c in WEATHER_DF.columns]
        # ensure consistent column names for lookup
        if "Province" in WEATHER_DF.columns:
            WEATHER_DF["Province"] = WEATHER_DF["Province"].astype(str).str.strip()
        if "Month" in WEATHER_DF.columns:
            WEATHER_DF["Month"] = WEATHER_DF["Month"].astype(str).str.strip().str.capitalize()
        # convert numeric columns where available (optional)
        for col in ["Avg_Temperature_C", "Avg_Rainfall_mm"]:
            if col in WEATHER_DF.columns:
                try:
                    WEATHER_DF[col] = pd.to_numeric(WEATHER_DF[col], errors="coerce")
                except Exception:
                    pass

if os.path.exists(EVENT_FILE):
    EVENT_DF = _safe_read_csv(EVENT_FILE, quotechar='"', escapechar='\\', engine='python')
    if EVENT_DF is not None:
        # Normalize column names
        EVENT_DF.columns = [c.strip() for c in EVENT_DF.columns]
        # Try to map possible column variants to expected names
        col_map = {}
        for c in EVENT_DF.columns:
            lc = c.lower()
            if 'event' in lc:
                col_map[c] = 'Event'
            elif 'category' in lc:
                col_map[c] = 'Category'
            elif 'location' in lc or 'locations' in lc:
                col_map[c] = 'Locations'
            elif 'start' in lc and 'month' in lc:
                col_map[c] = 'Start Month'
            elif 'end' in lc and 'month' in lc:
                col_map[c] = 'End Month'
            elif 'impact' in lc:
                col_map[c] = 'Impact'
        EVENT_DF = EVENT_DF.rename(columns=col_map)
        # Ensure required columns exist
        for needed in ['Event','Category','Locations','Start Month','End Month','Impact']:
            if needed not in EVENT_DF.columns:
                EVENT_DF[needed] = ""
        # Normalize text for columns used in lookup
        EVENT_DF['Locations'] = EVENT_DF['Locations'].astype(str).str.lower()
        EVENT_DF['Start Month'] = EVENT_DF['Start Month'].astype(str).str.strip().str.capitalize()
        EVENT_DF['End Month'] = EVENT_DF['End Month'].astype(str).str.strip().str.capitalize()

# Build event index for fast province lookup (if EVENT_DF loaded)
if EVENT_DF is not None:
    EVENT_INDEX = defaultdict(list)
    try:
        # Precompute a set of province keys (lowercase) for matching
        province_keys = set(REGION_TO_PROVINCE.values())
        # For each row, map it to provinces where it should be searchable
        for _, row in EVENT_DF.iterrows():
            locs = str(row.get("Locations", "")).lower()
            # If 'nationwide' present, include all provinces
            if "nationwide" in locs:
                for prov in province_keys:
                    EVENT_INDEX[prov].append(row.to_dict())
                continue
            # try to match any province key or region word
            matched = False
            for key, prov in REGION_TO_PROVINCE.items():
                if key in locs:
                    EVENT_INDEX[prov].append(row.to_dict())
                    matched = True
            # if no explicit mapping, also add to a special 'other' bucket
            if not matched:
                EVENT_INDEX["other"].append(row.to_dict())
    except Exception as e:
        # If indexing fails, set to None so we fallback to scanning
        logger.warning("Could not build event index: %s", e)
        EVENT_INDEX = None

# -------------------------
# Utility helpers
# -------------------------
def normalize_month(m: str) -> str:
    return (m or "").strip().capitalize()

def resolve_province(region_param: str) -> str:
    if not region_param:
        return "Western"
    key = region_param.strip().lower()
    return REGION_TO_PROVINCE.get(key, REGION_TO_PROVINCE.get(key.split()[-1], "Western"))

def month_in_range(m_start: str, m_end: str, m_query: str) -> bool:
    """Check inclusive month range; supports wrap-around from Dec->Jan"""
    try:
        s = MONTH2NUM[normalize_month(m_start)]
        e = MONTH2NUM[normalize_month(m_end)]
        q = MONTH2NUM[normalize_month(m_query)]
    except KeyError:
        return False
    if s <= e:
        return s <= q <= e
    return q >= s or q <= e

# -------------------------
# Cached helpers (really speed up repeated calls)
# -------------------------
# Cache Firebase forecast reads by date_key (YYYY-MM)
if HAS_FIREBASE:
    @lru_cache(maxsize=512)
    def cached_forecast(date_key: str):
        try:
            ref = db.reference("forecasts/prophet").child(date_key)
            return ref.get()
        except Exception as e:
            logger.warning("Firebase forecast read failed for %s: %s", date_key, e)
            return None
else:
    def cached_forecast(date_key: str):
        return None

# Cache weather lookups (province, month)
@lru_cache(maxsize=256)
def cached_weather(province: str, month: str):
    return load_weather_for(province, month)

# Cache events lookup (province, region, month) -> tuple(list) to be cacheable
@lru_cache(maxsize=256)
def cached_events(province: str, region_param: str, month: str):
    # Return tuple of dicts so it's hashable for lru_cache
    return tuple(fetch_events_for_impl(province, region_param, month))

# Cache top places - use a wrapper that calls existing top_places (which relies on Firebase)
@lru_cache(maxsize=128)
def get_top_places_cached(category: str, province: str):
    try:
        return top_places(category, province, top_k=10)
    except Exception as e:
        logger.warning("top_places error: %s", e)
        return []

# -------------------------
# Core data access helpers (fast, memory-backed)
# -------------------------
def load_weather_for(province: str, month_name: str):
    """Fast weather lookup using preloaded WEATHER_DF (if available)."""
    if WEATHER_DF is None:
        return {"temperature_c": None, "rainfall_mm": None, "note": "Weather file not found"}
    try:
        prov = (province or "").strip()
        m = normalize_month(month_name)
        # Case-insensitive matching
        rows = WEATHER_DF[(WEATHER_DF["Province"].str.lower() == prov.lower()) & (WEATHER_DF["Month"] == m)]
        if rows.empty:
            return {"temperature_c": None, "rainfall_mm": None, "note": "No province+month weather match"}
        r = rows.iloc[0]
        temp = float(r.get("Avg_Temperature_C")) if pd.notna(r.get("Avg_Temperature_C")) else None
        rain = float(r.get("Avg_Rainfall_mm")) if pd.notna(r.get("Avg_Rainfall_mm")) else None
        season_note = None
        if rain is not None:
            if rain >= 250:
                season_note = "High rainfall (monsoon)"
            elif rain >= 120:
                season_note = "Moderate rainfall"
            else:
                season_note = "Low rainfall"
        return {"temperature_c": temp, "rainfall_mm": rain, "note": season_note}
    except Exception as e:
        logger.exception("Error in load_weather_for: %s", e)
        return {"temperature_c": None, "rainfall_mm": None, "note": "Weather lookup error"}

def fetch_events_for_impl(province: str, region_param: str, month_name: str):
    """
    Internal implementation that returns a list (not cached).
    Uses EVENT_INDEX if available for O(1) province lookups; otherwise scans EVENT_DF.
    """
    matched = []
    prov_l = (province or "").lower()
    reg_l = (region_param or "").lower()
    q_month = normalize_month(month_name)

    # Use indexed lookup if available
    if EVENT_INDEX is not None:
        rows = EVENT_INDEX.get(province, []) + EVENT_INDEX.get("other", [])
        for row in rows:
            try:
                sm = normalize_month(row.get("Start Month", ""))
                em = normalize_month(row.get("End Month", ""))
                locs = str(row.get("Locations", "")).lower()
                if not sm or not em:
                    continue
                # If region or province matches (we already filtered by index) and month_in_range
                if month_in_range(sm, em, q_month):
                    matched.append({
                        "Event": str(row.get("Event", "")).strip(),
                        "Category": str(row.get("Category", "")).strip(),
                        "Locations": str(row.get("Locations", "")).strip(),
                        "Start Month": sm,
                        "End Month": em,
                        "Impact": str(row.get("Impact", "")).strip()
                    })
            except Exception:
                continue
        return matched

    # Fallback: scan EVENT_DF if loaded
    if EVENT_DF is not None:
        try:
            for _, row in EVENT_DF.iterrows():
                sm = normalize_month(str(row.get("Start Month", "")))
                em = normalize_month(str(row.get("End Month", "")))
                locs = str(row.get("Locations", "")).lower()
                if not sm or not em:
                    continue
                # match "nationwide" or province/region text within Locations
                if ("nationwide" in locs) or (prov_l and prov_l in locs) or (reg_l and reg_l in locs):
                    if month_in_range(sm, em, q_month):
                        matched.append({
                            "Event": str(row.get("Event", "")).strip(),
                            "Category": str(row.get("Category", "")).strip(),
                            "Locations": str(row.get("Locations", "")).strip(),
                            "Start Month": sm,
                            "End Month": em,
                            "Impact": str(row.get("Impact", "")).strip()
                        })
        except Exception as e:
            logger.exception("Error scanning EVENT_DF: %s", e)
        return matched

    # Last fallback: Firebase events node if available
    if HAS_FIREBASE:
        try:
            evs = db.reference("events").get() or {}
            for _, ev in evs.items():
                if not isinstance(ev, dict):
                    continue
                sm = normalize_month(str(ev.get("Start Month", "")))
                em = normalize_month(str(ev.get("End Month", "")))
                locs = str(ev.get("Locations", "")).lower()
                if not sm or not em:
                    continue
                if ("nationwide" in locs) or (prov_l and prov_l in locs) or (reg_l and reg_l in locs):
                    if month_in_range(sm, em, q_month):
                        matched.append({
                            "Event": str(ev.get("Event", "")).strip(),
                            "Category": str(ev.get("Category", "")).strip(),
                            "Locations": str(ev.get("Locations", "")).strip(),
                            "Start Month": sm,
                            "End Month": em,
                            "Impact": str(ev.get("Impact", "")).strip()
                        })
        except Exception as e:
            logger.warning("Firebase events read failed: %s", e)
    return matched

# -------------------------
# top_places function (unchanged behaviour)
# -------------------------
def top_places(category: str, province: str, top_k: int = 10):
    """
    Attempt to get top places from Firebase (fast) when available; otherwise return empty list.
    Kept same behavior as original function but we rely on cached wrapper to speed repeated calls.
    """
    if not HAS_FIREBASE:
        return []

    try:
        stats_ref = db.reference(f"review_stats/{category}")
        stats = stats_ref.get() or {}
        if not stats:
            return []

        ranked = []
        for place_id, s in stats.items():
            if not isinstance(s, dict):
                continue
            avg_sent = s.get("avg_sentiment_score", None)
            total = s.get("total_reviews", 0) or 0
            avg_rating = s.get("avg_rating", None)

            # --- OPTIMIZED PROVINCE RESOLUTION ---
            place_prov = ""
            name_lower = ""
            
            # Step 1: Check memory cache using place_id or name
            for key, prov_val in PLACE_METADATA_CACHE.items():
                # If key is name-based
                if key in place_id.lower():
                    place_prov = prov_val
                    break

            # Step 2: Only hit Firebase if cache missed
            sample_row = None
            if not place_prov:
                try:
                    sample_ref = db.reference(f"reviews/{category}/{place_id}")
                    sample = sample_ref.order_by_key().limit_to_first(1).get() or {}
                    for _, v in sample.items():
                        if isinstance(v, dict):
                            sample_row = v
                            place_prov = v.get("province", "")
                            break
                except Exception as e:
                    logger.warning("Metadata fetch failed for %s: %s", place_id, e)

            # Step 3: Final check - search name in cache
            if not place_prov and sample_row:
                name_lower = sample_row.get("name", "").lower()
                for key, prov_val in PLACE_METADATA_CACHE.items():
                    if key in name_lower:
                        place_prov = prov_val
                        break

            # Step 4: Province Filtering
            # If we STILL don't have a province, we briefly allow it to pass 
            # if the region is nationwide or if we're desperate for results.
            if province and place_prov and place_prov.lower() != province.lower():
                continue
            
            # Save newly found metadata to cache
            if place_prov and sample_row:
                clean_name = sample_row.get("name", "").lower()
                if clean_name:
                    PLACE_METADATA_CACHE[clean_name] = place_prov

            # --- REFINED COMPOSITE RANKING ---
            # Normalizing Sentiment (-1 to 1) to match Star Rating (0 to 5)
            # This ensures both metrics have EQUAL weight in the final "Top 10" order.
            sent_norm = (avg_sent + 1) * 2.5 if avg_sent is not None else 2.5
            rank_score = (avg_rating or 0) + sent_norm

            ranked.append({
                "place_id": place_id,
                "avg_sentiment": avg_sent if avg_sent is not None else None,
                "total_reviews": total,
                "avg_rating": avg_rating,
                "rank_score": rank_score,
                "name": (sample_row or {}).get("name", name_lower.title() or "Location"),
                "district": (sample_row or {}).get("district", ""),
                "province": place_prov,
                "photo_url": (sample_row or {}).get("photo_url", None),
            })

        # Unified sorting for both categories: High Rank Score -> More Reviews -> Top 10
        ranked.sort(key=lambda r: (r.get("rank_score") or 0, r.get("total_reviews") or 0), reverse=True)

        return ranked[:top_k]
    except Exception as e:
        logger.warning("Error in top_places: %s", e)
        return []

# -------------------------
# Natural language insight builder (kept same as original)
# -------------------------
def build_insight_text(region: str, month: str, forecast, events, weather, top_attr, top_hotels):
    insights = []

    if forecast:
        try:
            insights.append(f"🔹 Predicted arrivals: ~{int(forecast['yhat']):,} (range {int(forecast['lower']):,}–{int(forecast['upper']):,})")
        except Exception:
            insights.append(f"🔹 Predicted arrivals: {forecast.get('yhat') or 'N/A'}")

    if events:
        top_ev = events[0]
        name = top_ev.get("Event") or top_ev.get("event") or "Event"
        insights.append(f"🔹 Event: {name}")

    if weather:
        temp = weather.get("temperature_c")
        rain = weather.get("rainfall_mm")
        note = weather.get("note")
        weather_text = "🔹 Weather: "
        if temp is not None:
            weather_text += f"{round(temp)}°C, "
        if rain is not None:
            weather_text += f"{round(rain)} mm rain, "
        if note:
            weather_text += f"{note}"
        insights.append(weather_text.rstrip(", "))

    if top_attr and len(top_attr) > 0:
        names = [a.get("name") for a in top_attr[:3] if a.get("name")]
        if names:
            insights.append(f"🔹 Top attractions now: {', '.join(names)}")

    if top_hotels and len(top_hotels) > 0:
        names = [h.get("name") for h in top_hotels[:3] if h.get("name")]
        if names:
            insights.append(f"🔹 Best-reviewed hotels: {', '.join(names)}")

    return insights

# -------------------------
# The endpoint (optimized)
# -------------------------
@api_bp.route("/dashboard_insights")
def dashboard_insights():
    region = request.args.get("region", "Colombo")
    month_raw = request.args.get("month", "")
    year_raw = request.args.get("year", "")
    month = normalize_month(month_raw) if month_raw else MONTHS[datetime.utcnow().month - 1]
    province = resolve_province(region)

    # Forecast: Use the synchronized High-Precision Master Engine
    forecast = None
    try:
        month_num = MONTH2NUM.get(month)
        target_year = int(year_raw) if year_raw and year_raw.isdigit() else datetime.utcnow().year
        
        # Call the same engine used in the Trends tab
        monthly_forecast_dict = predict_monthly(target_year)
        yhat = monthly_forecast_dict.get(month, 0)
        
        # Format for dashboard (keeping keys compatible)
        forecast = {
            "period": f"{target_year}-{month_num:02d}",
            "yhat": yhat,
            "lower": yhat * 0.85, # Adaptive confidence interval for dashboard display
            "upper": yhat * 1.15
        }
    except Exception as e:
        logger.warning("Live forecast failed for dashboard: %s", e)
        forecast = None

    # Weather: fast cached lookup (uses in-memory WEATHER_DF)
    weather = cached_weather(province, month)

    # Events: cached; underlying fetch uses index or fallback
    try:
        events_tuple = cached_events(province, region, month)  # tuple of dicts
        events = list(events_tuple)
    except Exception:
        events = list(fetch_events_for_impl(province, region, month))

    # Top places: parallelize retrieval of attractions + hotels (cached wrapper called)
    top_attractions = []
    top_hotels = []
    try:
        # Use threadpool to fetch both in parallel and still use cached wrapper
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_attr = executor.submit(get_top_places_cached, "attractions", province)
            fut_hot = executor.submit(get_top_places_cached, "hotels", province)
            top_attractions = fut_attr.result(timeout=10) # INCREASED TIMEOUT
            top_hotels = fut_hot.result(timeout=10) # INCREASED TIMEOUT
    except Exception as e:
        logger.warning("Parallel top_places failed: %s", e)
        # fallback: sequential
        try:
            top_attractions = get_top_places_cached("attractions", province)
            top_hotels = get_top_places_cached("hotels", province)
        except Exception:
            top_attractions = []
            top_hotels = []

    # Build AI-style insights (same output structure)
    insight = build_insight_text(region, month, forecast, events, weather, top_attractions, top_hotels)

    resp = {
        "region": region,
        "province": province,
        "month": month,
        "year": year_raw or datetime.utcnow().year,
        "forecast": forecast,
        "weather": weather,
        "events": events,
        "top_attractions": top_attractions,
        "top_hotels": top_hotels,
        "insight": insight
    }
    return jsonify(resp), 200
