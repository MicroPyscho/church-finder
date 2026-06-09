"""
Geocoder service for Sanctuary.

Extracts UK postcodes from location strings and resolves them
to lat/lon using postcodes.io (free, no API key required).

Also contains the geographic centroid + radius search logic
for proximity-weighted location search.
"""
import re
import math
import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

# UK region centroids (lat, lon)
REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "london":          (51.5074, -0.1278),
    "kent":            (51.2787, 0.5217),
    "surrey":          (51.3148, -0.5600),
    "sussex":          (50.9500, -0.1000),
    "hampshire":       (51.0577, -1.3080),
    "berkshire":       (51.4500, -1.0000),
    "hertfordshire":   (51.8097, -0.2376),
    "essex":           (51.7343, 0.4691),
    "buckinghamshire": (51.8143, -0.8093),
    "oxfordshire":     (51.7520, -1.2577),
    "wiltshire":       (51.3492, -1.9927),
    "dorset":          (50.7487, -2.3444),
    "somerset":        (51.1050, -2.9262),
    "devon":           (50.7156, -3.5309),
    "cornwall":        (50.2660, -5.0527),
    "gloucestershire": (51.8642, -2.2380),
    "worcestershire":  (52.1911, -2.2200),
    "warwickshire":    (52.2816, -1.5848),
    "northamptonshire":(52.2405, -0.9027),
    "leicestershire":  (52.6369, -1.1398),
    "nottinghamshire": (53.0000, -1.0800),
    "derbyshire":      (53.1047, -1.5624),
    "staffordshire":   (52.8793, -2.0573),
    "shropshire":      (52.7077, -2.7440),
    "herefordshire":   (52.0565, -2.7150),
    "west midlands":   (52.4862, -1.8904),
    "cheshire":        (53.1981, -2.8913),
    "lancashire":      (53.7632, -2.7044),
    "manchester":      (53.4808, -2.2426),
    "merseyside":      (53.4084, -2.9916),
    "yorkshire":       (53.9591, -1.0815),
    "cumbria":         (54.5772, -2.7975),
    "durham":          (54.7761, -1.5733),
    "northumberland":  (55.2000, -1.9800),
    "norfolk":         (52.6309, 1.2974),
    "suffolk":         (52.1872, 0.9708),
    "cambridgeshire":  (52.2053, 0.1218),
    "lincolnshire":    (53.2307, -0.5396),
    "wales":           (52.1307, -3.7837),
    "scotland":        (56.4907, -4.2026),
    "edinburgh":       (55.9533, -3.1883),
    "glasgow":         (55.8642, -4.2518),
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two lat/lon points."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def proximity_score(distance_miles: float) -> int:
    """
    Onion-ring proximity scoring from region centroid.
    Ring 1 (0-15mi):   100% — core region
    Ring 2 (15-35mi):   90% — outer region
    Ring 3 (35-75mi):   80% — adjacent counties
    Ring 4 (75-120mi):  70% — wider area
    Ring 5 (120-200mi): 60% — same broad region
    Beyond 200mi:       excluded — different region
    """
    if distance_miles <= 15:   return 100
    if distance_miles <= 35:   return 90
    if distance_miles <= 75:   return 80
    if distance_miles <= 120:  return 70
    if distance_miles <= 200:  return 60
    return 0  # excluded


def extract_postcode(text: str) -> str | None:
    """Extract UK postcode from any text string."""
    if not text:
        return None
    m = re.search(
        r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b',
        text.upper()
    )
    if m:
        return m.group(1).replace(" ", "").upper()
    # Also try outward code only (e.g. "E8", "SW9", "OL14")
    m2 = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?)\b', text.upper())
    if m2:
        return m2.group(1)
    return None


async def geocode_postcode(postcode: str) -> tuple[float, float] | None:
    """Resolve postcode to (lat, lon) using postcodes.io."""
    try:
        clean = postcode.replace(" ", "").upper()
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"https://api.postcodes.io/postcodes/{clean}")
            if r.status_code == 200:
                data = r.json().get("result", {})
                lat = data.get("latitude")
                lon = data.get("longitude")
                if lat and lon:
                    return float(lat), float(lon)
            # Try outward code
            r2 = await c.get(f"https://api.postcodes.io/outcodes/{clean}")
            if r2.status_code == 200:
                data = r2.json().get("result", {})
                lat = data.get("latitude")
                lon = data.get("longitude")
                if lat and lon:
                    return float(lat), float(lon)
    except Exception as e:
        logger.debug("Geocode failed for %s: %s", postcode, e)
    return None


async def geocode_listing(location: str) -> tuple[float, float] | None:
    """
    Geocode a listing location string.
    Tries postcode extraction first, then falls back to region centroid.
    """
    if not location:
        return None

    # Try to extract and geocode a postcode
    pc = extract_postcode(location)
    if pc:
        result = await geocode_postcode(pc)
        if result:
            return result

    # Fall back to region centroid matching
    loc_lower = location.lower()
    for region, centroid in REGION_CENTROIDS.items():
        if region in loc_lower:
            return centroid

    return None


async def geocode_all_listings(db) -> int:
    """
    Geocode all listings that don't have lat/lon yet.
    Updates the DB in place. Returns count of geocoded listings.
    """
    from sqlalchemy import text

    rows = (await db.execute(text(
        "SELECT id, location FROM listings "
        "WHERE is_active = true "
        "AND (geocoded = false OR geocoded IS NULL) "
        "AND location IS NOT NULL "
        "LIMIT 200"
    ))).all()

    if not rows:
        return 0

    geocoded = 0
    for row in rows:
        try:
            result = await geocode_listing(row.location)
            if result:
                lat, lon = result
                await db.execute(text(
                    "UPDATE listings SET lat=:lat, lon=:lon, geocoded=true WHERE id=:id"
                ), {"lat": lat, "lon": lon, "id": row.id})
                geocoded += 1
            else:
                # Mark as attempted even if failed
                await db.execute(text(
                    "UPDATE listings SET geocoded=true WHERE id=:id"
                ), {"id": row.id})
        except Exception as e:
            logger.warning("Geocode listing %s failed: %s", row.id, e)
        await asyncio.sleep(0.1)  # Rate limit postcodes.io

    await db.commit()
    logger.info("Geocoded %d/%d listings", geocoded, len(rows))
    return geocoded


def get_location_centroid(query: str) -> tuple[float, float] | None:
    """Extract location from query and return its centroid."""
    from app.services.location_tiers import detect_location
    key = detect_location(query)
    if key and key in REGION_CENTROIDS:
        return REGION_CENTROIDS[key]
    return None
