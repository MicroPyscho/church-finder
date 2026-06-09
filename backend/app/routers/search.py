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
from app.services.groq_client import parse_search_intent

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword sets (used for DB filtering and relevance checks)
# ---------------------------------------------------------------------------

CHURCH_KEYWORDS = {
    "church", "churches", "chapel", "chapels", "ecclesiastical",
    "worship", "place of worship", "nave", "vestry", "tabernacle",
    "minster", "priory", "abbey", "cathedral", "meeting house",
    "mission hall", "methodist", "baptist", "gospel hall", "kingdom hall",
    "village hall", "community hall", "assembly hall", "masonic",
    "memorial hall", "drill hall", "civic hall", "parish hall",
    "church hall", "church building", "religious building",
    "united reformed", "salvation army", "quaker", "evangelical",
    "pentecostal", "diocese", "converted chapel", "former church",
    "redundant church", "church conversion", "sacred", "congregation",
    "sanctuary", "local church", "place of gathering",
}

LOCATION_WORDS = {
    "london","kent","surrey","essex","sussex","hampshire","somerset","devon",
    "cornwall","dorset","wiltshire","gloucestershire","oxfordshire","berkshire",
    "hertfordshire","buckinghamshire","suffolk","norfolk","cambridgeshire",
    "lincolnshire","nottinghamshire","derbyshire","leicestershire",
    "northamptonshire","warwickshire","worcestershire","herefordshire",
    "shropshire","staffordshire","cheshire","lancashire","yorkshire",
    "durham","northumberland","cumbria","wales","scotland","ireland",
    "midlands","north","south","east","west","england","uk","britain",
    "nationwide","anywhere",
}

STOPWORDS = {
    "a","an","the","and","or","for","in","on","at","to","of","with",
    "near","around","by","is","are","was","were","be","have","has",
}


# ---------------------------------------------------------------------------
# Intent parsing — Groq-powered with deterministic fallback
# ---------------------------------------------------------------------------

def _deterministic_intent(query: str) -> dict:
    """Fast deterministic fallback if Groq is unavailable."""
    q = query.lower().strip()
    words = re.findall(r"[\w']+", q)
    intent = {
        "price_max": None, "price_min": None,
        "locations": [], "features": [],
        "listing_type": "any", "intent_type": "explore",
        "keywords": [], "is_relevant_query": True,
        "confidence": 0.5, "property_type": None,
        "use_case": None, "denomination": None,
        "follow_up_questions": [],
    }
    # Price
    for m in re.finditer(r'£\s*([\d,]+)\s*[kK]?', q):
        val = int(m.group(1).replace(",", ""))
        if "k" in m.group(0).lower():
            val *= 1000
        intent["price_max"] = val
    # Locations
    locs = [w for w in words if w in LOCATION_WORDS]
    for loc in ["north west","north east","south east","south west",
                "east midlands","west midlands","east anglia"]:
        if loc in q:
            locs.append(loc)
    intent["locations"] = list(dict.fromkeys(l.title() for l in locs))
    # Listing type
    if any(w in q for w in ["auction","auctioned"]):
        intent["listing_type"] = "auction"
    elif any(w in q for w in ["let","rent","lease"]):
        intent["listing_type"] = "let"
    elif any(w in q for w in ["sale","buy","purchase"]):
        intent["listing_type"] = "sale"
    # Features
    feats = []
    if any(w in q for w in ["parking","car park","garage"]):
        feats.append("parking")
    if any(w in q for w in ["graveyard","cemetery","churchyard"]):
        feats.append("graveyard")
    if any(w in q for w in ["hall","meeting room"]):
        feats.append("hall")
    if any(w in q for w in ["spire","tower","steeple"]):
        feats.append("spire")
    intent["features"] = feats
    # Keywords
    kws = [w for w in words if w not in STOPWORDS and w not in LOCATION_WORDS and len(w) >= 3 and not re.match(r'^\d+$', w)]
    intent["keywords"] = kws[:8]
    # Relevance
    all_text = " ".join(words)
    is_church = any(kw in all_text for kw in CHURCH_KEYWORDS)
    is_property = any(w in all_text for w in [
        "property","building","space","premises","site","land",
        "conversion","development","affordable","former","redundant",
    ])
    if not (is_church or is_property or intent["price_max"] or intent["locations"]):
        intent["is_relevant_query"] = False
        intent["confidence"] = 0.1
    elif is_church:
        intent["confidence"] = 0.9
        intent["intent_type"] = "specific"
    else:
        intent["confidence"] = 0.7
    return intent


async def get_intent(query: str) -> dict:
    """
    Parse search intent using Groq LLM.
    Falls back to deterministic parser if Groq fails.
    """
    try:
        groq_result = await parse_search_intent(query)

        # Merge Groq result with deterministic base
        base = _deterministic_intent(query)
        base.update({
            "locations":           groq_result.get("locations") or base["locations"],
            "price_max":           groq_result.get("price_max") or base["price_max"],
            "price_min":           groq_result.get("price_min") or base["price_min"],
            "features":            groq_result.get("features") or base["features"],
            "property_type":       groq_result.get("property_type"),
            "use_case":            groq_result.get("use_case"),
            "listing_type":        groq_result.get("listing_type") or base["listing_type"],
            "denomination":        groq_result.get("denomination"),
            "follow_up_questions": _format_follow_up(
                groq_result.get("follow_up_questions", []), base
            ),
        })
        return base

    except Exception as e:
        logger.warning("Groq intent failed, using fallback: %s", e)
        intent = _deterministic_intent(query)
        intent["follow_up_questions"] = _static_follow_up(intent)
        return intent


def _format_follow_up(groq_questions: list, intent: dict) -> list:
    """
    Convert Groq's plain string questions into structured follow-up objects
    with relevant answer options.
    """
    result = []
    for i, q in enumerate(groq_questions[:2]):
        if not q or not isinstance(q, str):
            continue
        q_lower = q.lower()
        # Determine options based on question content
        if any(w in q_lower for w in ["budget","price","cost","afford","£"]):
            options = ["Under £100k","£100k–£250k","£250k–£500k","£500k–£1m","Over £1m","Flexible"]
        elif any(w in q_lower for w in ["area","location","where","region","county","part"]):
            options = ["London","South East","South West","Midlands","North of England","Wales","Scotland","Nationwide"]
        elif any(w in q_lower for w in ["use","purpose","intend","plan","doing","convert"]):
            options = ["Active worship","Community use","Residential conversion","Commercial conversion","Investment","Unsure"]
        elif any(w in q_lower for w in ["size","capacity","seats","large","small","sqft","sq ft"]):
            options = ["Small (under 200 sqft)","Medium (200–1000 sqft)","Large (1000–3000 sqft)","Very large (3000+ sqft)","Flexible"]
        elif any(w in q_lower for w in ["denomination","type","methodist","baptist","catholic","anglican"]):
            options = ["Any denomination","Methodist","Baptist","Anglican/CoE","Catholic","Non-denominational","Other"]
        elif any(w in q_lower for w in ["auction","buy","sale","how"]):
            options = ["Private sale","Auction","Either","Open to offers"]
        elif any(w in q_lower for w in ["listed","heritage","historic","grade"]):
            options = ["Listed building fine","Prefer unlisted","Either"]
        else:
            options = ["Yes","No","Not sure","Tell me more"]
        result.append({"id": f"q{i}", "question": q, "options": options})
    return result


def _static_follow_up(intent: dict) -> list:
    """Static fallback follow-up questions when Groq is unavailable."""
    questions = []
    if not intent["price_max"]:
        questions.append({
            "id": "budget", "question": "What is your budget?",
            "options": ["Under £100k","£100k–£250k","£250k–£500k","£500k–£1m","Over £1m","Flexible"],
        })
    if not intent["locations"]:
        questions.append({
            "id": "location", "question": "Where in the UK are you looking?",
            "options": ["London","South East","South West","Midlands","North of England","Wales","Scotland","Nationwide"],
        })
    return questions[:2]


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query:    str
    filters:  dict = {}
    page:     int  = 1
    per_page: int  = 20


@router.post("")
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    intent = await get_intent(req.query)

    if not intent.get("is_relevant_query", True):
        return {
            "intent": intent,
            "results": [], "total": 0,
            "page": req.page, "per_page": req.per_page,
            "is_relevant_query": False,
            "edge_case": "not_church_query",
            "follow_up_questions": [],
        }

    # Base query
    q = select(Listing).where(Listing.is_active == True)

    # Location filter
    if intent["locations"]:
        q = q.where(or_(
            *[Listing.location.ilike(f"%{loc}%") for loc in intent["locations"]]
        ))

    # Specific keyword filter
    specific_keywords = [
        kw for kw in intent.get("keywords", [])
        if kw not in CHURCH_KEYWORDS and kw not in LOCATION_WORDS
        and kw not in {"affordable","cheap","large","small","historic","old",
                       "former","available","listed","heritage"}
    ]
    if specific_keywords:
        q = q.where(or_(*[
            or_(Listing.title.ilike(f"%{kw}%"), Listing.description.ilike(f"%{kw}%"))
            for kw in specific_keywords[:4]
        ]))

    # Count
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()

    # Paginate
    q = q.order_by(Listing.first_seen.desc())
    q = q.offset((req.page - 1) * req.per_page).limit(req.per_page)
    rows = (await db.execute(q)).scalars().all()

    # Score
    results = []
    for listing in rows:
        criteria = _build_criteria(listing, intent)
        score    = _compute_score(criteria, listing, intent)
        results.append(_to_dict(listing, score, criteria))

    results.sort(key=lambda x: x["_score"], reverse=True)

    return {
        "intent":               intent,
        "results":              results,
        "total":                total,
        "pages":                (total + req.per_page - 1) // req.per_page,
        "page":                 req.page,
        "per_page":             req.per_page,
        "is_relevant_query":    True,
        "follow_up_questions":  intent.get("follow_up_questions", []),
    }


# ---------------------------------------------------------------------------
# Analysis stream — Groq-powered property summary
# ---------------------------------------------------------------------------

@router.get("/stream-analysis/{property_id}")
async def stream_analysis(property_id: str, db: AsyncSession = Depends(get_db)):
    prop = await db.get(Listing, property_id)
    if not prop:
        return StreamingResponse(iter(["Property not found"]), media_type="text/plain")

    async def generate():
        from app.services.groq_client import chat
        try:
            system = """You are a UK property analyst specialising in churches and chapels.
Write a concise, informative analysis of this property listing for a potential buyer.
Cover: key features, potential uses, considerations, and any notable aspects.
Be factual, professional and helpful. 200-250 words."""

            user_msg = f"""Property: {prop.title}
Location: {prop.location}
Price: {prop.price or 'POA'}
Source: {prop.source}
Description: {prop.description or 'No description available.'}

Write the property analysis."""

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ]
            result = await chat(messages=messages, temperature=0.5, max_tokens=400)
            for chunk in result.split(" "):
                yield chunk + " "
                await __import__("asyncio").sleep(0.03)
        except Exception as e:
            logger.warning("Stream analysis failed: %s", e)
            # Fallback to static text
            text = (
                f"## {prop.title}\n\n"
                f"**Source:** {prop.source}  \n"
                f"**Location:** {prop.location}  \n"
                f"**Price:** {prop.price or 'POA'}  \n\n"
                f"{prop.description or 'No description available.'}\n\n"
                f"Key considerations:\n"
                f"- Verify planning permissions for intended use\n"
                f"- Commission a structural survey before purchase\n"
                f"- Check listed building status with Historic England\n"
            )
            for chunk in text.split(" "):
                yield chunk + " "
                await __import__("asyncio").sleep(0.02)

    return StreamingResponse(generate(), media_type="text/plain")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_criteria(listing: Listing, intent: dict) -> list:
    criteria = []
    if intent.get("price_max"):
        m = re.search(r'£([\d,]+)', listing.price or "")
        if m:
            val = int(m.group(1).replace(",", ""))
            if val <= intent["price_max"]:
                criteria.append({"label": f"Under £{intent['price_max']//1000}k", "status": "exact", "detail": listing.price})
            elif val <= intent["price_max"] * 1.2:
                criteria.append({"label": f"Near £{intent['price_max']//1000}k", "status": "close", "detail": listing.price})
            else:
                criteria.append({"label": f"Over £{intent['price_max']//1000}k", "status": "miss", "detail": listing.price})
    if intent.get("locations"):
        loc = (listing.location or "").lower()
        hit = any(l.lower() in loc for l in intent["locations"])
        criteria.append({"label": intent["locations"][0], "status": "exact" if hit else "miss"})
    if intent.get("listing_type") and intent["listing_type"] != "any":
        lt = (listing.source or "").lower()
        is_auction = any(w in lt for w in ["auction","emson","allsop","sdl","eig","btg"])
        if intent["listing_type"] == "auction":
            criteria.append({"label": "Auction", "status": "exact" if is_auction else "miss"})
    return criteria


def _compute_score(criteria: list, listing: Listing, intent: dict) -> int:
    if not criteria:
        return {
            "Alex Martin Commercial": 95, "Clive Emson Auctions": 90,
            "Church of England": 88, "Church Growth Trust": 88,
            "Churches Conservation Trust": 85, "SW Property": 88,
            "BTG Eddisons Auctions": 85,
        }.get(listing.source, 75)
    exact = sum(1 for c in criteria if c["status"] == "exact")
    close = sum(1 for c in criteria if c["status"] == "close")
    raw   = round(((exact + close * 0.6) / len(criteria)) * 100)
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
    return {
        "id": listing.id, "source": listing.source,
        "source_url": listing.url, "title": listing.title,
        "price_raw": listing.price, "price": listing.price,
        "location": listing.location, "county": "",
        "description": listing.description, "images": images,
        "image_url": images[0] if images else None,
        "listing_type": "sale", "is_off_market": listing.is_off_market,
        "has_parking": False, "has_graveyard": False,
        "has_hall": False, "has_spire": False,
        "first_seen": listing.first_seen.isoformat(),
        "last_seen": listing.last_seen.isoformat(),
        "is_active": listing.is_active,
        "_score": score, "_criteria": criteria,
    }
