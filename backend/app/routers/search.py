import json
import logging
import re
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from pydantic import BaseModel

from app.database import get_db
from app.models import Listing

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent parser
# ---------------------------------------------------------------------------

CHURCH_KEYWORDS = {
    "church", "chapel", "ecclesiastical", "worship", "nave", "vestry",
    "tabernacle", "minster", "priory", "abbey", "meeting house", "mission hall",
    "methodist", "baptist", "gospel hall", "kingdom hall", "village hall",
    "community hall", "assembly hall", "masonic", "memorial hall", "drill hall",
    "civic hall", "parish hall", "place of worship", "united reformed",
    "salvation army", "quaker", "evangelical", "pentecostal", "diocese",
    "converted chapel", "former church", "redundant church", "church conversion",
    "sacred", "congregation", "sanctuary",
}

LOCATION_WORDS = {
    "london","kent","surrey","essex","sussex","hampshire","somerset","devon",
    "cornwall","dorset","wiltshire","gloucestershire","oxfordshire","berkshire",
    "hertfordshire","buckinghamshire","suffolk","norfolk","cambridgeshire",
    "lincolnshire","nottinghamshire","derbyshire","leicestershire","northamptonshire",
    "warwickshire","worcestershire","herefordshire","shropshire","staffordshire",
    "cheshire","lancashire","yorkshire","durham","northumberland","cumbria",
    "wales","scotland","ireland","midlands","north","south","east","west",
    "england","uk","britain","nationwide","anywhere",
}

PRICE_RE = re.compile(r'£\s*([\d,]+)\s*[kK]?')
STOPWORDS = {"a","an","the","and","or","for","in","on","at","to","of","with",
             "near","around","by","is","are","was","were","be","have","has"}


def parse_intent(query: str) -> dict:
    q = query.lower().strip()
    words = re.findall(r"[\w']+", q)

    intent = {
        "price_max": None,
        "locations": [],
        "features": [],
        "listing_type": "any",
        "intent_type": "explore",
        "keywords": [],
        "is_relevant_query": True,
        "confidence": 0.5,
    }

    # Price
    for m in PRICE_RE.finditer(q):
        val = int(m.group(1).replace(",", ""))
        if "k" in m.group(0).lower():
            val *= 1000
        intent["price_max"] = val

    # Locations
    locs = []
    for w in words:
        if w in LOCATION_WORDS:
            locs.append(w)
    # Also look for multi-word county names
    for loc in ["north west","north east","south east","south west","east midlands",
                "west midlands","east anglia","isle of wight","isle of man"]:
        if loc in q:
            locs.append(loc)
    intent["locations"] = list(dict.fromkeys(l.title() for l in locs))

    # Listing type
    if any(w in q for w in ["auction","auctioned","going to auction"]):
        intent["listing_type"] = "auction"
    elif any(w in q for w in ["let","rent","lease","letting"]):
        intent["listing_type"] = "let"
    elif any(w in q for w in ["sale","buy","purchase","for sale"]):
        intent["listing_type"] = "sale"

    # Features
    feats = []
    if any(w in q for w in ["parking","car park","garage"]):
        feats.append("parking")
    if any(w in q for w in ["graveyard","cemetery","churchyard","burial"]):
        feats.append("graveyard")
    if any(w in q for w in ["hall","meeting room","community space"]):
        feats.append("hall")
    if any(w in q for w in ["spire","tower","steeple"]):
        feats.append("spire")
    intent["features"] = feats

    # Keywords — only non-stopword, non-location, non-common words
    kws = []
    for w in words:
        if w in STOPWORDS or w in LOCATION_WORDS:
            continue
        if len(w) < 3:
            continue
        if re.match(r'^\d+$', w):
            continue
        kws.append(w)
    intent["keywords"] = kws[:8]

    # Relevance check — is this a church/property query?
    all_text = " ".join(words)
    is_church = any(kw in all_text for kw in CHURCH_KEYWORDS)
    is_property = any(w in all_text for w in [
        "property","building","space","premises","site","land",
        "conversion","development","planning","listed",
        "affordable","cheap","cheap","expensive","large","small",
        "historic","heritage","old","former","redundant","available",
    ])
    is_price = intent["price_max"] is not None
    is_location = bool(intent["locations"])

    if not (is_church or is_property or is_price or is_location):
        intent["is_relevant_query"] = False
        intent["confidence"] = 0.1
    elif is_church:
        intent["confidence"] = 0.9
        intent["intent_type"] = "specific"
    elif is_property or is_price:
        intent["confidence"] = 0.7
        intent["intent_type"] = "explore"

    return intent


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query:    str
    filters:  dict   = {}
    page:     int    = 1
    per_page: int    = 20


@router.post("")
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    intent = parse_intent(req.query)

    if not intent["is_relevant_query"]:
        return {
            "intent": intent,
            "results": [],
            "total": 0,
            "page": req.page,
            "per_page": req.per_page,
            "is_relevant_query": False,
            "edge_case": "not_church_query",
            "follow_up_questions": [],
        }

    # Base query — all active listings
    q = select(Listing).where(Listing.is_active == True)

    # Location filter
    if intent["locations"]:
        loc_filters = [
            Listing.location.ilike(f"%{loc}%")
            for loc in intent["locations"]
        ]
        q = q.where(or_(*loc_filters))

    # Keyword filter — only apply if query has specific non-generic keywords
    # Generic words like "church", "chapel" etc match ALL listings by intent
    # so we skip the DB filter and let scoring handle ranking
    specific_keywords = [
        kw for kw in intent["keywords"]
        if kw not in CHURCH_KEYWORDS and kw not in LOCATION_WORDS
        and kw not in {"affordable","cheap","large","small","historic","old","former","available","listed","heritage"}
    ]

    if specific_keywords:
        kw_filters = [
            or_(
                Listing.title.ilike(f"%{kw}%"),
                Listing.description.ilike(f"%{kw}%"),
            )
            for kw in specific_keywords[:4]
        ]
        q = q.where(or_(*kw_filters))

    # Price filter
    if intent["price_max"]:
        # Can't filter string prices perfectly — show all and score
        pass

    # Count total
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    q = q.order_by(Listing.first_seen.desc())
    q = q.offset((req.page - 1) * req.per_page).limit(req.per_page)
    rows = (await db.execute(q)).scalars().all()

    # Score and build results
    results = []
    for listing in rows:
        criteria = _build_criteria(listing, intent)
        score = _compute_score(criteria, listing, intent)
        results.append(_to_dict(listing, score, criteria))

    # Sort by score descending
    results.sort(key=lambda x: x["_score"], reverse=True)

    return {
        "intent": intent,
        "results": results,
        "total": total,
        "page": req.page,
        "per_page": req.per_page,
        "is_relevant_query": True,
        "follow_up_questions": _follow_up_questions(intent),
    }


# ---------------------------------------------------------------------------
# Analysis stream endpoint
# ---------------------------------------------------------------------------

@router.get("/stream-analysis/{property_id}")
async def stream_analysis(property_id: str, db: AsyncSession = Depends(get_db)):
    prop = await db.get(Listing, property_id)
    if not prop:
        return StreamingResponse(iter(["Property not found"]), media_type="text/plain")

    async def generate():
        text = (
            f"## {prop.title}\n\n"
            f"**Source:** {prop.source}  \n"
            f"**Location:** {prop.location}  \n"
            f"**Price:** {prop.price or 'POA'}  \n\n"
            f"### About this property\n\n"
            f"{prop.description or 'No description available.'}\n\n"
            f"### Key considerations\n\n"
            f"- Verify planning permissions for intended use\n"
            f"- Commission a structural survey before purchase\n"
            f"- Check listed building status with Historic England\n"
            f"- Review any restrictive covenants on the title\n"
            f"- Confirm utility connections and access rights\n"
        )
        for chunk in text.split(" "):
            yield chunk + " "
            await __import__("asyncio").sleep(0.03)

    return StreamingResponse(generate(), media_type="text/plain")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _follow_up_questions(intent: dict) -> list:
    questions = []
    if not intent["price_max"]:
        questions.append({
            "id": "budget",
            "question": "What is your budget?",
            "options": ["Under £100k","£100k–£250k","£250k–£500k","£500k–£1m","Over £1m","Flexible"],
        })
    if not intent["locations"]:
        questions.append({
            "id": "location",
            "question": "Where in the UK are you looking?",
            "options": ["London","South East","South West","Midlands","North of England","Wales","Scotland","Nationwide"],
        })
    if intent["listing_type"] == "any":
        questions.append({
            "id": "listing_type",
            "question": "Are you looking to buy or rent?",
            "options": ["Buy outright","Auction","Lease / Rent","Any"],
        })
    return questions[:2]


def _build_criteria(listing: Listing, intent: dict) -> list:
    criteria = []

    # Price
    if intent["price_max"]:
        price_str = listing.price or ""
        m = re.search(r'£([\d,]+)', price_str)
        if m:
            val = int(m.group(1).replace(",", ""))
            if val <= intent["price_max"]:
                criteria.append({"label": f"Under £{intent['price_max']//1000}k", "status": "exact", "detail": price_str})
            elif val <= intent["price_max"] * 1.2:
                criteria.append({"label": f"Near £{intent['price_max']//1000}k", "status": "close", "detail": price_str})
            else:
                criteria.append({"label": f"Over £{intent['price_max']//1000}k", "status": "miss", "detail": price_str})

    # Location
    if intent["locations"]:
        loc = (listing.location or "").lower()
        hit = any(l.lower() in loc for l in intent["locations"])
        criteria.append({"label": intent["locations"][0], "status": "exact" if hit else "miss"})

    # Listing type
    if intent["listing_type"] != "any":
        lt = (listing.source or "").lower()
        is_auction = any(w in lt for w in ["auction","emson","allsop","sdl","eig"])
        if intent["listing_type"] == "auction":
            criteria.append({"label": "Auction", "status": "exact" if is_auction else "miss"})

    return criteria


def _compute_score(criteria: list, listing: Listing, intent: dict) -> int:
    if not criteria:
        # No criteria — base score on source quality
        source_scores = {
            "Alex Martin Commercial": 95,
            "Clive Emson Auctions": 90,
            "Church of England": 88,
            "Church Growth Trust": 88,
            "Churches Conservation Trust": 85,
            "OnTheMarket": 80,
            "Church in Wales": 85,
            "Church of Scotland": 85,
        }
        return source_scores.get(listing.source, 75)

    exact = sum(1 for c in criteria if c["status"] == "exact")
    close = sum(1 for c in criteria if c["status"] == "close")
    total = len(criteria)
    raw = round(((exact + close * 0.6) / total) * 100)
    if raw >= 95: return 100
    if raw >= 85: return 90
    if raw >= 75: return 80
    if raw >= 65: return 70
    if raw >= 50: return 60
    return 30


def _to_dict(listing: Listing, score: int, criteria: list) -> dict:
    images = []
    try:
        images = json.loads(listing.images) if listing.images else []
    except:
        pass

    def safe(attr, default=None):
        return getattr(listing, attr, default)

    return {
        "id":            listing.id,
        "source":        listing.source,
        "source_url":    listing.url,
        "title":         listing.title,
        "price_raw":     listing.price,
        "price":         listing.price,
        "location":      listing.location,
        "county":        safe("county", ""),
        "description":   listing.description,
        "images":        images,
        "image_url":     images[0] if images else None,
        "listing_type":  safe("listing_type", "sale"),
        "is_listed":     safe("is_listed", False),
        "listed_grade":  safe("listed_grade", ""),
        "is_off_market": safe("is_off_market", False),
        "has_parking":   safe("has_parking", False),
        "has_graveyard": safe("has_graveyard", False),
        "has_hall":      safe("has_hall", False),
        "has_spire":     safe("has_spire", False),
        "first_seen":    listing.first_seen.isoformat(),
        "last_seen":     listing.last_seen.isoformat(),
        "is_active":     listing.is_active,
        "_score":        score,
        "_criteria":     criteria,
    }
