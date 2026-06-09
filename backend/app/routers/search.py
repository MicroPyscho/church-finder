"""
Search router — clean, simple, fast.

Flow:
  1. Groq parses natural language query into structured intent (locations, price, keywords)
  2. Standard Postgres query using those structured fields
  3. Score and return results

Groq never touches the database. It only translates language to structure.
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

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Church synonym expansion — used in DB query only
# When user says "church", also search for chapel, worship etc in the DB
# ---------------------------------------------------------------------------

SYNONYMS = {
    "church":     ["church", "chapel", "ecclesiastical", "worship", "nave",
                   "vestry", "tabernacle", "minster", "priory", "abbey",
                   "cathedral", "gospel hall", "meeting house", "religious"],
    "chapel":     ["chapel", "church", "methodist", "baptist", "wesleyan",
                   "gospel hall", "meeting house", "tabernacle", "ecclesiastical"],
    "worship":    ["worship", "church", "chapel", "ecclesiastical",
                   "congregation", "parish", "religious", "place of worship"],
    "hall":       ["hall", "church hall", "community hall", "village hall",
                   "assembly hall", "parish hall", "memorial hall", "gathering"],
    "community":  ["community", "village hall", "church hall", "assembly hall",
                   "gathering space", "meeting house"],
    "methodist":  ["methodist", "wesleyan", "primitive methodist", "chapel"],
    "baptist":    ["baptist", "chapel", "gospel hall"],
    "cathedral":  ["cathedral", "minster", "church", "abbey", "priory"],
    "religious":  ["church", "chapel", "worship", "ecclesiastical", "religious"],
}

def expand_terms(keywords: list[str]) -> list[str]:
    """Expand search keywords to include all synonyms."""
    expanded = set()
    for kw in keywords:
        kl = kw.lower()
        if kl in SYNONYMS:
            expanded.update(SYNONYMS[kl])
        else:
            expanded.add(kl)
    return list(expanded)


# ---------------------------------------------------------------------------
# Price extraction from DB string values
# ---------------------------------------------------------------------------

def extract_price(price_str: str) -> int | None:
    """Extract integer from strings like '£125,000' or '£100k-£200k'."""
    if not price_str:
        return None
    m = re.search(r"£([\d,]+)\s*[kK]?", price_str)
    if not m:
        return None
    val = int(m.group(1).replace(",", ""))
    if "k" in m.group(0).lower():
        val *= 1000
    return val


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

    # ── Step 1: Parse intent with Groq ────────────────────────────────────
    # Groq translates natural language → structured fields.
    # This is its ONLY job. It never sees the database.
    intent = await parse_search_intent(req.query)

    # ── Step 2: Build DB query from structured intent ─────────────────────
    q = select(Listing).where(Listing.is_active == True)

    # Location filter — Groq expands "near London" to surrounding counties
    locations = intent.get("locations", [])
    if locations:
        q = q.where(or_(
            *[Listing.location.ilike(f"%{loc}%") for loc in locations]
        ))

    # Keyword filter — expand synonyms so "church" finds chapel/worship etc
    # Extract meaningful words from the query directly (not from intent keywords)
    query_words = [
        w.lower() for w in re.findall(r"[a-zA-Z]+", req.query)
        if w.lower() not in {
            "a","an","the","and","or","for","in","on","at","to","of","with",
            "near","around","by","is","are","i","me","my","we","looking",
            "want","need","find","search","some","any","about","please",
            "within","hours","drive","from","under","above","below","between",
            "affordable","cheap","large","small","old","former","available",
        }
        and len(w) > 3
    ]

    # Expand synonyms
    search_terms = expand_terms(query_words)

    # Only apply keyword filter if we have meaningful non-generic terms
    generic = {"church","chapel","worship","religious","building","property",
               "space","place","gathering","hall","ecclesiastical"}
    specific_terms = [t for t in search_terms if t not in generic]

    if specific_terms:
        # Has specific terms (e.g. "methodist", "yorkshire", "conversion")
        q = q.where(or_(*[
            or_(
                Listing.title.ilike(f"%{t}%"),
                Listing.description.ilike(f"%{t}%"),
            )
            for t in specific_terms[:8]
        ]))
    else:
        # Generic query like "church" or "place of worship" — return everything
        # but still search for ANY church synonym to exclude non-church listings
        all_synonyms = list(set(
            term for terms in SYNONYMS.values() for term in terms
        ))
        q = q.where(or_(*[
            or_(
                Listing.title.ilike(f"%{t}%"),
                Listing.description.ilike(f"%{t}%"),
                Listing.source.ilike(f"%{t}%"),
            )
            for t in all_synonyms[:15]
        ]))

    # ── Step 3: Count and paginate ────────────────────────────────────────
    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    q = q.order_by(Listing.first_seen.desc())
    q = q.offset((req.page - 1) * req.per_page).limit(req.per_page)
    rows = (await db.execute(q)).scalars().all()

    # ── Step 4: Score results ─────────────────────────────────────────────
    price_min = intent.get("price_min") or 0
    price_max = intent.get("price_max")

    results = []
    for listing in rows:
        # Price range filter
        lp = extract_price(listing.price or "")
        if lp is not None:
            if price_max and lp > price_max * 1.1:
                continue
            if price_min and lp < price_min * 0.9:
                continue

        criteria = _build_criteria(listing, intent)
        score    = _compute_score(criteria, listing)
        results.append(_to_dict(listing, score, criteria))

    results.sort(key=lambda x: x["_score"], reverse=True)
    total = len(results)

    return {
        "intent":              intent,
        "results":             results,
        "total":               total,
        "pages":               max(1, (total + req.per_page - 1) // req.per_page),
        "page":                req.page,
        "per_page":            req.per_page,
        "is_relevant_query":   True,
        "follow_up_questions": _format_follow_up(intent),
    }


# ---------------------------------------------------------------------------
# Property analysis stream
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_follow_up(intent: dict) -> list:
    """Convert Groq follow-up questions to structured options."""
    result = []
    for i, q in enumerate(intent.get("follow_up_questions", [])[:2]):
        if not q or not isinstance(q, str):
            continue
        q_lower = q.lower()
        if any(w in q_lower for w in ["budget","price","cost","£"]):
            options = ["Under £100k","£100k–£250k","£250k–£500k","£500k+","Flexible"]
        elif any(w in q_lower for w in ["where","location","area","region","county"]):
            options = ["London","South East","South West","Midlands","North England","Wales","Scotland","Nationwide"]
        elif any(w in q_lower for w in ["use","purpose","intend","plan","convert"]):
            options = ["Active worship","Community use","Residential conversion","Commercial","Investment"]
        elif any(w in q_lower for w in ["size","capacity","large","small"]):
            options = ["Small","Medium","Large","Very large","Flexible"]
        elif any(w in q_lower for w in ["denomination","type","methodist","baptist"]):
            options = ["Any","Methodist","Baptist","Anglican","Catholic","Non-denominational"]
        else:
            options = ["Yes","No","Not sure"]
        result.append({"id": f"q{i}", "question": q, "options": options})
    return result


def _build_criteria(listing: Listing, intent: dict) -> list:
    criteria = []
    price_val = extract_price(listing.price or "")
    price_max = intent.get("price_max")
    price_min = intent.get("price_min") or 0

    if price_val and (price_max or price_min):
        in_range = (
            (not price_max or price_val <= price_max) and
            (not price_min or price_val >= price_min)
        )
        label = f"£{price_min//1000}k–£{price_max//1000}k" if price_min and price_max else \
                f"Under £{price_max//1000}k" if price_max else \
                f"Over £{price_min//1000}k"
        criteria.append({
            "label": label,
            "status": "exact" if in_range else "miss",
            "detail": listing.price,
        })

    if intent.get("locations"):
        loc = (listing.location or "").lower()
        hit = any(l.lower() in loc for l in intent["locations"])
        criteria.append({
            "label": intent["locations"][0],
            "status": "exact" if hit else "miss",
        })

    return criteria


def _compute_score(criteria: list, listing: Listing) -> int:
    if not criteria:
        return {
            "Alex Martin Commercial": 95,
            "Church of England": 90,
            "SW Property": 90,
            "Church Growth Trust": 88,
            "Churches Conservation Trust": 85,
            "Clive Emson Auctions": 83,
            "BTG Eddisons Auctions": 82,
        }.get(listing.source, 75)

    exact = sum(1 for c in criteria if c["status"] == "exact")
    raw   = round((exact / len(criteria)) * 100)
    if raw >= 90: return 100
    if raw >= 70: return 85
    if raw >= 50: return 70
    return 50


def _to_dict(listing: Listing, score: int, criteria: list) -> dict:
    images = []
    try:
        images = json.loads(listing.images) if listing.images else []
    except Exception:
        pass
    return {
        "id":            listing.id,
        "source":        listing.source,
        "source_url":    listing.url,
        "title":         listing.title,
        "price_raw":     listing.price,
        "price":         listing.price,
        "location":      listing.location,
        "description":   listing.description,
        "images":        images,
        "image_url":     images[0] if images else None,
        "listing_type":  "sale",
        "is_off_market": listing.is_off_market,
        "first_seen":    listing.first_seen.isoformat(),
        "last_seen":     listing.last_seen.isoformat(),
        "is_active":     listing.is_active,
        "_score":        score,
        "_criteria":     criteria,
    }
