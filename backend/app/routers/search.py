from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, text
from app.database import get_db
from app.models import Listing
import json, math, re, logging

logger = logging.getLogger(__name__)
router = APIRouter()

CHURCH_KEYWORDS = [
    "church","chapel","ecclesiastical","vestry","nave","place of worship",
    "tabernacle","minster","priory","abbey","meeting house","mission hall",
    "former church","methodist","baptist","gospel hall","kingdom hall",
    "village hall","community hall","assembly hall","masonic hall",
    "memorial hall","drill hall","civic hall","parish hall",
    "former theatre","former cinema","bingo hall","former school",
    "graveyard","churchyard","presbytery","converted chapel",
    "converted church","church conversion",
]

LOCATIONS = [
    "kent","surrey","sussex","east sussex","west sussex","hampshire",
    "berkshire","oxfordshire","buckinghamshire","hertfordshire","essex",
    "suffolk","norfolk","cambridgeshire","lincolnshire","yorkshire",
    "north yorkshire","south yorkshire","west yorkshire","lancashire",
    "gloucestershire","wiltshire","somerset","devon","dorset","cornwall",
    "derbyshire","nottinghamshire","leicestershire","staffordshire",
    "warwickshire","northamptonshire","shropshire","cheshire","cumbria",
    "scotland","wales","london","manchester","birmingham","bristol",
    "liverpool","leeds","sheffield","newcastle","edinburgh","glasgow",
    "cardiff","isle of wight",
]

PRICE_RE = [
    (re.compile(r'under\s*£?([\d,]+)\s*k', re.I),       lambda m: int(m.group(1).replace(",",""))*1000),
    (re.compile(r'under\s*£?([\d,]+)', re.I),            lambda m: int(m.group(1).replace(",",""))),
    (re.compile(r'below\s*£?([\d,]+)\s*k', re.I),        lambda m: int(m.group(1).replace(",",""))*1000),
    (re.compile(r'less\s*than\s*£?([\d,]+)\s*k', re.I),  lambda m: int(m.group(1).replace(",",""))*1000),
    (re.compile(r'max\s*£?([\d,]+)\s*k', re.I),          lambda m: int(m.group(1).replace(",",""))*1000),
    (re.compile(r'up\s*to\s*£?([\d,]+)\s*k', re.I),      lambda m: int(m.group(1).replace(",",""))*1000),
    (re.compile(r'£([\d,]+)', re.I),                     lambda m: int(m.group(1).replace(",",""))),
    (re.compile(r'([\d,]+)\s*k\b', re.I),                lambda m: int(m.group(1).replace(",",""))*1000),
    (re.compile(r'half\s*a?\s*million', re.I),            lambda m: 500_000),
]

LOC_RE = re.compile(
    r'\b(' + '|'.join(re.escape(l) for l in sorted(LOCATIONS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)

FEATURE_RE = {
    "parking":   re.compile(r'parking|car park|garage', re.I),
    "graveyard": re.compile(r'graveyard|churchyard|burial ground|cemetery', re.I),
    "hall":      re.compile(r'\bhall\b|parish hall|community hall', re.I),
    "spire":     re.compile(r'spire|tower|bell tower|steeple', re.I),
}

INTENT_RE = {
    "buy_convert":  re.compile(r'convert|conversion|change of use|develop|development potential|planning permission', re.I),
    "buy_preserve": re.compile(r'preserve|restoration|restore|heritage|listed building|historic|conservation', re.I),
    "buy_use":      re.compile(r'use as (a )?church|congregation|worship service|plant a church|start a church', re.I),
}

AUCTION_RE = re.compile(r'\bauction\b|\blot\b', re.I)


def parse_intent(query: str) -> dict:
    q = query.strip()
    ql = q.lower()
    intent = {
        "price_max": None, "locations": [], "features": [],
        "listing_type": "any", "intent_type": "explore",
        "keywords": [], "is_relevant_query": True, "confidence": 0.5,
    }

    # Relevance check
    if not any(kw in ql for kw in CHURCH_KEYWORDS):
        intent["is_relevant_query"] = False
        return intent

    # Price
    for pattern, extractor in PRICE_RE:
        m = pattern.search(q)
        if m:
            try:
                val = extractor(m)
                if 5_000 <= val <= 50_000_000:
                    intent["price_max"] = val
                    break
            except: pass

    # Location
    locs = LOC_RE.findall(q)
    if locs:
        intent["locations"] = list(dict.fromkeys(l.title() for l in locs))

    # Features
    for feat, pattern in FEATURE_RE.items():
        if pattern.search(q):
            intent["features"].append(feat)

    # Intent type
    for itype, pattern in INTENT_RE.items():
        if pattern.search(q):
            intent["intent_type"] = itype
            break

    # Auction
    if AUCTION_RE.search(q):
        intent["listing_type"] = "auction"

    # Keywords for text search
    stopwords = {"a","an","the","in","on","at","for","with","and","or","to","of",
                 "is","are","i","me","my","want","need","looking","find","show",
                 "get","please","can","could","would","like","most","very",
                 "affordable","cheap","good","large","big","small"}
    words = re.findall(r'\b[a-z]{3,}\b', ql)
    intent["keywords"] = [w for w in words if w not in stopwords][:8]

    # Confidence
    signals = sum([
        bool(intent["price_max"]),
        bool(intent["locations"]),
        bool(intent["features"]),
        intent["intent_type"] != "explore",
        intent["listing_type"] != "any",
    ])
    intent["confidence"] = min(0.95, 0.4 + signals * 0.12)
    return intent


def score_listing(listing: Listing, intent: dict) -> tuple[int, list]:
    criteria = []
    score_num = 0.0
    score_den = 0

    if intent.get("price_max"):
        score_den += 2
        # Try to parse price from string
        price_str = listing.price or ""
        pm = re.search(r'£([\d,]+)', price_str)
        price_val = int(pm.group(1).replace(",","")) if pm else None
        if price_val and price_val <= intent["price_max"]:
            criteria.append({"label": f"Under £{intent['price_max']//1000}k", "status": "exact", "detail": price_str})
            score_num += 2
        elif price_val and price_val <= intent["price_max"] * 1.15:
            criteria.append({"label": f"Near £{intent['price_max']//1000}k", "status": "close", "detail": price_str})
            score_num += 1.2
        elif price_val:
            criteria.append({"label": f"Over £{intent['price_max']//1000}k", "status": "miss", "detail": price_str})

    if intent.get("locations"):
        score_den += 2
        loc = (listing.location or "").lower()
        hit = any(l.lower() in loc for l in intent["locations"])
        if hit:
            criteria.append({"label": intent["locations"][0], "status": "exact"})
            score_num += 2
        else:
            criteria.append({"label": intent["locations"][0], "status": "miss"})

    if intent.get("listing_type") not in ("any",""):
        score_den += 1
        lt = getattr(listing, "listing_type", "sale") or "sale"
        if lt == intent["listing_type"]:
            criteria.append({"label": intent["listing_type"].capitalize(), "status": "exact"})
            score_num += 1
        else:
            criteria.append({"label": intent["listing_type"].capitalize(), "status": "miss"})

    pct = round((score_num / score_den) * 100) if score_den else 100
    return pct, criteria[:6]


class SearchRequest(BaseModel):
    query:    str    = ""
    filters:  dict   = {}
    page:     int    = 1
    per_page: int    = 20
    sort_by:  str    = "relevance"


@router.post("")
async def search(body: SearchRequest, db: AsyncSession = Depends(get_db)):
    query = body.query.strip()

    # Empty query — return recent listings
    if not query or len(query) < 2:
        q = select(Listing).where(
            Listing.is_active == True
        ).order_by(Listing.first_seen.desc()).limit(body.per_page)
        rows = (await db.execute(q)).scalars().all()
        total = len(rows)
        results = []
        for r in rows:
            results.append(_to_dict(r, 100, []))
        return {
            "intent": {"is_relevant_query": True, "keywords": []},
            "results": results, "total": total,
            "page": 1, "pages": 1, "facets": {},
            "query_time_ms": 0, "follow_up_questions": [],
            "is_relevant_query": True,
        }

    # Parse intent
    intent = parse_intent(query)

    # Non-relevant query
    if not intent["is_relevant_query"]:
        return {
            "is_relevant_query": False,
            "message": "Sanctuary covers churches, chapels, halls, and gathering spaces across the UK.",
            "suggestions": [
                "Church for sale in Kent",
                "Former chapel with parking, Yorkshire",
                "Community hall with large capacity",
                "Methodist church under £200k",
            ],
        }

    # Build SQL query
    q = select(Listing).where(Listing.is_active == True)

    # Keyword text search
    if intent["keywords"]:
        kw_filters = [
            or_(
                Listing.title.ilike(f"%{kw}%"),
                Listing.description.ilike(f"%{kw}%"),
            )
            for kw in intent["keywords"][:4]
        ]
        q = q.where(or_(*kw_filters))

    # Price filter
    if intent.get("price_max"):
        price_pattern = f"£%"
        # We filter loosely since price is stored as string
        # Exact price matching done in scoring

    # Location filter
    if intent.get("locations"):
        loc_filters = [
            Listing.location.ilike(f"%{loc}%")
            for loc in intent["locations"]
        ]
        q = q.where(or_(*loc_filters))

    # Sort
    if body.sort_by == "price_asc":
        q = q.order_by(Listing.price.asc())
    elif body.sort_by == "price_desc":
        q = q.order_by(Listing.price.desc())
    else:
        q = q.order_by(Listing.first_seen.desc())

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Broaden if zero results
    broadened = False
    broaden_reason = ""
    if total == 0 and intent.get("locations"):
        q_broad = select(Listing).where(Listing.is_active == True)
        if intent["keywords"]:
            kw_filters = [or_(Listing.title.ilike(f"%{kw}%"), Listing.description.ilike(f"%{kw}%")) for kw in intent["keywords"][:4]]
            q_broad = q_broad.where(or_(*kw_filters))
        q_broad = q_broad.order_by(Listing.first_seen.desc())
        total = (await db.execute(select(func.count()).select_from(q_broad.subquery()))).scalar_one()
        if total > 0:
            q = q_broad
            broadened = True
            broaden_reason = f"No results in {', '.join(intent['locations'])} — showing all UK results"

    # Paginate
    q = q.offset((body.page - 1) * body.per_page).limit(body.per_page)
    rows = (await db.execute(q)).scalars().all()

    # Score
    results = []
    for r in rows:
        score, criteria = score_listing(r, intent)
        results.append(_to_dict(r, score, criteria))

    if body.sort_by == "relevance":
        results.sort(key=lambda x: x["_score"], reverse=True)

    pages = max(1, math.ceil(total / body.per_page))

    response = {
        "intent": intent,
        "results": results,
        "total": total,
        "page": body.page,
        "pages": pages,
        "facets": {},
        "query_time_ms": 0,
        "is_relevant_query": True,
        "follow_up_questions": _follow_ups(intent, total),
    }
    if broadened:
        response["broadened"] = True
        response["broaden_reason"] = broaden_reason
    return response


def _follow_ups(intent: dict, total: int) -> list:
    q = []
    if intent.get("intent_type") == "explore":
        q.append("What would you like to use the property for?")
    if not intent.get("features"):
        q.append("Any specific features? (parking, hall, graveyard…)")
    if not intent.get("price_max"):
        q.append("Do you have a budget in mind?")
    if total > 30 and not intent.get("locations"):
        q.append("Would you like to narrow by county?")
    return q[:2]


def _to_dict(listing: Listing, score: int, criteria: list) -> dict:
    import json
    images = []
    try:
        images = json.loads(listing.images) if listing.images else []
    except: pass
    def safe(attr, default=None):
        return getattr(listing, attr, default)
    return {
        "id":            listing.id,
        "source":        listing.source,
        "source_url":    listing.url,
        "title":         listing.title,
        "price_raw":     listing.price,
        "price_gbp":     safe("price_gbp"),
        "location":      listing.location,
        "county":        safe("county", ""),
        "description":   listing.description,
        "images":        images,
        "image_url":     images[0] if images else None,
        "listing_type":  safe("listing_type", "sale"),
        "is_listed":     safe("is_listed", False),
        "listed_grade":  safe("listed_grade", ""),
        "is_off_market": safe("is_off_market", False),
        "first_seen":    listing.first_seen.isoformat(),
        "last_seen":     listing.last_seen.isoformat(),
        "_score":        score,
        "_criteria":     criteria,
    }

@router.get("/stream-analysis/{property_id}")
async def stream_analysis(property_id: str, db: AsyncSession = Depends(get_db)):
    prop = await db.get(Listing, property_id)
    if not prop:
        from fastapi import HTTPException
        raise HTTPException(404, "Property not found")

    async def generate():
        msg = f"Analysis for {prop.title}. Located in {prop.location}. Listed at {prop.price}. "
        if prop.description:
            msg += prop.description[:200]
        yield f"data: {json.dumps({'text': msg})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
