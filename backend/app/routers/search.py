"""
Search router — simple, fast, clean.

Groq: natural language → structured intent (price, location, keywords)
DB:   ilike search across title + location + description
No keyword filtering. No stopwords. The DB is already clean.
"""
import json
import logging
import re
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from pydantic import BaseModel

from app.database import get_db
from app.models import Listing
from app.services.groq_client import parse_search_intent
from app.services.location_tiers import get_tiers, detect_location
from app.services.geocoder import get_location_centroid, haversine, proximity_score

router = APIRouter()
logger = logging.getLogger(__name__)

# Church synonyms — expand user terms to catch all related listings
SYNONYMS = {
    # Plurals and stems map to same search terms
    "church":       ["church", "chapel", "ecclesiastical", "worship", "nave",
                     "vestry", "tabernacle", "minster", "priory", "abbey",
                     "cathedral", "gospel hall", "meeting house"],
    "churches":     ["church", "chapel", "ecclesiastical", "worship", "nave",
                     "vestry", "tabernacle", "minster", "priory", "abbey",
                     "cathedral", "gospel hall", "meeting house"],
    "chapel":       ["chapel", "church", "methodist", "baptist", "wesleyan",
                     "gospel hall", "meeting house", "tabernacle"],
    "chapels":      ["chapel", "church", "methodist", "baptist", "wesleyan",
                     "gospel hall", "meeting house", "tabernacle"],
    "worship":      ["worship", "church", "chapel", "ecclesiastical",
                     "congregation", "parish"],
    "worshipping":  ["worship", "church", "chapel", "ecclesiastical"],
    "hall":         ["hall", "church hall", "community hall", "village hall",
                     "assembly hall", "parish hall", "memorial hall"],
    "halls":        ["hall", "church hall", "community hall", "village hall"],
    "cathedral":    ["cathedral", "minster", "church", "abbey", "priory"],
    "cathedrals":   ["cathedral", "minster", "church", "abbey", "priory"],
    "methodist":    ["methodist", "wesleyan", "chapel"],
    "methodists":   ["methodist", "wesleyan", "chapel"],
    "baptist":      ["baptist", "chapel", "gospel hall"],
    "baptists":     ["baptist", "chapel", "gospel hall"],
    "religious":    ["church", "chapel", "worship", "ecclesiastical"],
    "ecclesiastical":["church", "chapel", "ecclesiastical", "worship"],
    "abbey":        ["abbey", "priory", "minster", "church"],
    "abbeys":       ["abbey", "priory", "minster", "church"],
    "priory":       ["priory", "abbey", "minster", "church"],
    "priories":     ["priory", "abbey", "minster", "church"],
    "minster":      ["minster", "cathedral", "church", "abbey"],
    "minsters":     ["minster", "cathedral", "church", "abbey"],
}

def expand(words: list[str]) -> list[str]:
    out = set()
    for w in words:
        out.update(SYNONYMS.get(w, [w]))
    return list(out)

def extract_price(s: str) -> int | None:
    if not s:
        return None
    m = re.search(r"£([\d,]+)\s*[kK]?", s)
    if not m:
        return None
    v = int(m.group(1).replace(",", ""))
    return v * 1000 if "k" in m.group(0).lower() else v


class SearchRequest(BaseModel):
    query:    str
    filters:  dict = {}
    page:     int  = 1
    per_page: int  = 20


@router.post("")
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):

    # Step 1 — Groq parses natural language into structured intent
    intent = await parse_search_intent(req.query)

    # Step 2 — Build DB query
    q = select(Listing).where(Listing.is_active == True)

    # ── Tiered location search ───────────────────────────────────────────
    # Tier 1: exact area terms (100% match)
    # Tier 2: neighbouring areas (85% match)
    # Tier 3: wider region (70% match)
    # No location filter = return all listings
    tiers = get_tiers(req.query)
    location_key = detect_location(req.query)
    intent["locations"] = [location_key.title()] if location_key else []

    centroid = get_location_centroid(req.query) if location_key else None

    if centroid and tiers:
        # Geo search: fetch all geocoded listings, score by distance
        # Also include tier terms as fallback for non-geocoded listings
        exact_terms = tiers.get("exact", [])
        near_terms  = tiers.get("near", [])
        all_terms   = list(dict.fromkeys(exact_terms + near_terms))
        short = [t for t in all_terms if len(t) <= 4][:15]
        long  = [t for t in all_terms if len(t) > 4][:8]
        use_terms = list(dict.fromkeys(short + long))
        if use_terms:
            q = q.where(or_(
                Listing.lat.isnot(None),  # has coordinates
                *[Listing.location.ilike(f"%{t}%") for t in use_terms]
            ))
    elif tiers:
        exact_terms = tiers.get("exact", [])
        near_terms  = tiers.get("near", [])
        all_terms   = list(dict.fromkeys(exact_terms + near_terms))
        short = [t for t in all_terms if len(t) <= 4][:15]
        long  = [t for t in all_terms if len(t) > 4][:8]
        use_terms = list(dict.fromkeys(short + long))
        if use_terms:
            q = q.where(or_(
                *[Listing.location.ilike(f"%{t}%") for t in use_terms]
            ))

    # Keywords: take every meaningful word from the query,
    # expand synonyms, search title + description + location.
    # No stopwords. No restrictions. DB is already clean.
    words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", req.query)]
    # Only skip pure connectives
    skip = {
        # Articles and conjunctions
        "the","and","or","but","a","an",
        # Prepositions — "church IN london", "chapel NEAR york"
        "in","at","on","of","to","by","up",
        "for","from","with","into","onto","upon",
        "near","around","within","outside","inside",
        "about","above","below","under","over",
        "between","among","across","along","beside",
        # Common query filler
        "that","this","have","been","they","there",
        "looking","want","find","some","any","please",
        "show","list","get","give","tell","search",
        "like","just","also","only","very","quite",
    }
    words = [w for w in words if w not in skip]

    if words:
        terms = expand(words)[:12]
        q = q.where(or_(*[
            or_(
                Listing.title.ilike(f"%{t}%"),
                Listing.description.ilike(f"%{t}%"),
                Listing.location.ilike(f"%{t}%"),
            )
            for t in terms
        ]))

    # Step 3 — Count and paginate
    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    rows = (await db.execute(
        q.order_by(Listing.first_seen.desc())
         .offset((req.page - 1) * req.per_page)
         .limit(req.per_page)
    )).scalars().all()

    # Step 4 — Score with price filter
    price_min = intent.get("price_min") or 0
    price_max = intent.get("price_max")

    results = []
    MAX_RADIUS = 200  # miles — beyond this, different region entirely

    for listing in rows:
        # Price filter
        lp = extract_price(listing.price or "")
        if lp is not None:
            if price_max and lp > price_max * 1.1:
                continue
            if price_min and lp < price_min * 0.9:
                continue

        # Onion-ring proximity scoring
        geo_score = None
        distance  = None
        if centroid and listing.lat and listing.lon:
            distance = haversine(centroid[0], centroid[1], listing.lat, listing.lon)
            # Beyond max radius = different region, exclude
            if distance > MAX_RADIUS:
                continue
            geo_score = proximity_score(distance)

        # Non-geocoded listing with location search:
        # Check if location text matches the search region
        if location_key and not listing.lat:
            tiers_data = get_tiers(req.query) or {}
            all_terms = tiers_data.get("exact",[]) + tiers_data.get("near",[])
            loc_text = (listing.location or "").lower()
            text_hit = any(t.lower() in loc_text for t in all_terms if len(t) > 2)
            if not text_hit:
                continue
            # Give text-matched non-geocoded listing a mid score
            geo_score = 75

        criteria = _criteria(listing, intent, location_key)
        base     = _score(criteria, listing)
        score    = geo_score if geo_score is not None else base
        result   = _to_dict(listing, score, criteria)
        if distance is not None:
            result["_distance_miles"] = round(distance, 1)
        results.append(result)

    results.sort(key=lambda x: x["_score"], reverse=True)

    return {
        "intent":             intent,
        "results":            results,
        "total":              len(results),
        "pages":              max(1, (total + req.per_page - 1) // req.per_page),
        "page":               req.page,
        "per_page":           req.per_page,
        "is_relevant_query":  True,
        "follow_up_questions": _follow_up(intent),
    }


@router.get("/stream-analysis/{property_id}")
async def stream_analysis(property_id: str, db: AsyncSession = Depends(get_db)):
    prop = await db.get(Listing, property_id)
    if not prop:
        return StreamingResponse(iter(["Property not found"]), media_type="text/plain")

    async def generate():
        from app.services.groq_client import chat
        try:
            result = await chat(
                messages=[
                    {"role": "system", "content": "You are a UK property analyst. Write a concise 200-word analysis of this church property for a potential buyer. Be factual and helpful."},
                    {"role": "user", "content": f"Property: {prop.title}\nLocation: {prop.location}\nPrice: {prop.price}\nDescription: {(prop.description or '')[:500]}"},
                ],
                temperature=0.5, max_tokens=300,
            )
            for chunk in result.split(" "):
                yield chunk + " "
                await __import__("asyncio").sleep(0.03)
        except Exception:
            yield f"{prop.title}\n{prop.location}\n{prop.price or 'POA'}\n\n{prop.description or ''}"

    return StreamingResponse(generate(), media_type="text/plain")


# ── Helpers ────────────────────────────────────────────────────────────────

def _follow_up(intent: dict) -> list:
    result = []
    for i, q in enumerate((intent.get("follow_up_questions") or [])[:2]):
        if not q:
            continue
        ql = q.lower()
        if any(w in ql for w in ["budget","price","cost","£"]):
            opts = ["Under £100k","£100k–£250k","£250k–£500k","£500k+","Flexible"]
        elif any(w in ql for w in ["where","location","area","region"]):
            opts = ["London","South East","Midlands","North England","Wales","Scotland","Nationwide"]
        elif any(w in ql for w in ["use","purpose","convert","plan"]):
            opts = ["Active worship","Community use","Conversion","Investment"]
        elif any(w in ql for w in ["denomination","type","methodist","baptist"]):
            opts = ["Any","Methodist","Baptist","Anglican","Catholic"]
        else:
            opts = ["Yes","No","Not sure"]
        result.append({"id": f"q{i}", "question": q, "options": opts})
    return result


def _criteria(listing: Listing, intent: dict, location_key: str = None) -> list:
    out = []
    lp = extract_price(listing.price or "")
    pm = intent.get("price_max")
    pn = intent.get("price_min") or 0
    if lp and (pm or pn):
        in_range = (not pm or lp <= pm) and (not pn or lp >= pn)
        label = f"Under £{pm//1000}k" if pm and not pn else \
                f"Over £{pn//1000}k" if pn and not pm else \
                f"£{pn//1000}k–£{pm//1000}k"
        out.append({"label": label,
                    "status": "exact" if in_range else "miss",
                    "detail": listing.price})
    if intent.get("locations") and location_key:
        loc = (listing.location or "").lower()
        tier_data = get_tiers(location_key) or {}
        exact_t = [t.lower() for t in tier_data.get("exact", [])]
        near_t  = [t.lower() for t in tier_data.get("near", [])]
        is_exact = any(t in loc for t in exact_t)
        is_near  = any(t in loc for t in near_t)
        status = "exact" if is_exact else "close" if is_near else "miss"
        out.append({"label": intent["locations"][0],
                    "status": status})
    return out


def _score(criteria: list, listing: Listing) -> int:
    if not criteria:
        return {"Alex Martin Commercial": 95, "Church of England": 90,
                "SW Property": 90, "Church Growth Trust": 88,
                "Churches Conservation Trust": 85}.get(listing.source, 75)
    exact = sum(1 for c in criteria if c["status"] == "exact")
    raw = round((exact / len(criteria)) * 100)
    return 100 if raw >= 90 else 85 if raw >= 70 else 70 if raw >= 50 else 50


def _to_dict(listing: Listing, score: int, criteria: list) -> dict:
    images = []
    try:
        images = json.loads(listing.images) if listing.images else []
    except Exception:
        pass
    return {
        "id": listing.id, "source": listing.source,
        "source_url": listing.url, "title": listing.title,
        "price_raw": listing.price, "price": listing.price,
        "location": listing.location, "description": listing.description,
        "images": images, "image_url": images[0] if images else None,
        "listing_type": "sale", "is_off_market": listing.is_off_market,
        "first_seen": listing.first_seen.isoformat(),
        "last_seen": listing.last_seen.isoformat(),
        "is_active": listing.is_active,
        "_score": score, "_criteria": criteria,
    }
