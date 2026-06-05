"""
Multi-source deterministic search agent.
Architecture:
  parse_intent (regex, 90% of queries)
    → LLM fallback only if confidence < 0.8
  plan_tools (pure if/else)
  execute tools in parallel (pure SQL)
  score + rank (pure Python)
  LLM synthesis only on demand (analysis card)

No LLM is called for normal search. Zero API cost per query.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

from sqlalchemy import select, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.intent import parse_intent_deterministic, plan_tools, ParsedIntent
from app.models import Listing
from app.keywords import matches_keywords

logger = logging.getLogger(__name__)


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    listings:      list[dict]
    total:         int
    page:          int
    pages:         int
    intent:        dict
    facets:        dict
    query_ms:      float
    used_llm:      bool   = False
    broadened:     bool   = False
    broaden_reason: str   = ""


# ── Main agent ───────────────────────────────────────────────────────────────

async def search_agent(
    query:    str,
    db:       AsyncSession,
    page:     int  = 1,
    per_page: int  = 20,
    sort_by:  str  = "relevance",
    filters:  dict = None,
) -> SearchResult:
    """
    The agent. Deterministic first, LLM only as last resort.
    """
    t0      = time.monotonic()
    filters = filters or {}
    used_llm = False

    # ── Step 1: Parse intent ─────────────────────────────────────────────────
    intent = parse_intent_deterministic(query)

    # LLM fallback only if confidence is low AND we have an API key
    if intent.confidence < 0.8:
        intent = await _llm_intent_fallback(query, intent)
        used_llm = True

    # Merge any explicit frontend filters over parsed intent
    intent = _merge_filters(intent, filters)

    # ── Step 2: Non-church query — return early ──────────────────────────────
    if not intent.is_relevant:
        return SearchResult(
            listings=[], total=0, page=page, pages=0,
            intent=_intent_to_dict(intent),
            facets={}, query_ms=0, used_llm=used_llm,
        )

    # ── Step 3: Plan tools ───────────────────────────────────────────────────
    tools = plan_tools(intent)

    # ── Step 4: Execute SQL queries in parallel ──────────────────────────────
    results = await asyncio.gather(
        _sql_filter(intent, tools, db, page, per_page, sort_by),
        _compute_facets(db),
        return_exceptions=True,
    )

    listings_page, facets = results
    if isinstance(listings_page, Exception):
        logger.error("SQL filter failed: %s", listings_page)
        listings_page = ([], 0)
    if isinstance(facets, Exception):
        facets = {}

    rows, total = listings_page

    # ── Step 5: If empty, broaden and retry ─────────────────────────────────
    broadened      = False
    broaden_reason = ""
    if total == 0 and _can_broaden(intent):
        intent, broaden_reason = _broaden_intent(intent)
        rows, total = await _sql_filter(intent, tools, db, page, per_page, sort_by)
        broadened = True

    # ── Step 6: Score and annotate ───────────────────────────────────────────
    scored = [_score_listing(row, intent) for row in rows]
    scored.sort(key=lambda x: x["_score"], reverse=True)

    import math
    pages    = max(1, math.ceil(total / per_page))
    query_ms = round((time.monotonic() - t0) * 1000, 1)

    return SearchResult(
        listings       = scored,
        total          = total,
        page           = page,
        pages          = pages,
        intent         = _intent_to_dict(intent),
        facets         = facets if isinstance(facets, dict) else {},
        query_ms       = query_ms,
        used_llm       = used_llm,
        broadened      = broadened,
        broaden_reason = broaden_reason,
    )


# ── SQL filter tool ──────────────────────────────────────────────────────────

async def _sql_filter(
    intent:   ParsedIntent,
    tools:    dict,
    db:       AsyncSession,
    page:     int,
    per_page: int,
    sort_by:  str,
) -> tuple[list[dict], int]:
    """
    Pure SQL. No LLM. Builds query from intent fields.
    """
    q = select(Listing).where(
        Listing.is_active == True,
        Listing.is_off_market == False,
    )

    # Keyword text search
    if tools.get("text_search") and intent.keywords:
        kw_filters = [
            or_(
                Listing.title.ilike(f"%{kw}%"),
                Listing.description.ilike(f"%{kw}%"),
            )
            for kw in intent.keywords[:5]
        ]
        q = q.where(or_(*kw_filters))

    # Price
    if intent.price_max:
        q = q.where(
            or_(Listing.price_gbp <= intent.price_max, Listing.price_gbp.is_(None))
        )
    if intent.price_min:
        q = q.where(
            or_(Listing.price_gbp >= intent.price_min, Listing.price_gbp.is_(None))
        )

    # Location
    if intent.locations:
        loc_filters = [
            or_(
                Listing.location.ilike(f"%{loc}%"),
                Listing.county.ilike(f"%{loc}%"),
            )
            for loc in intent.locations
        ]
        q = q.where(or_(*loc_filters))

    # Listing type
    if tools.get("auction_filter"):
        q = q.where(Listing.listing_type == "auction")
    elif intent.listing_type not in ("any", ""):
        q = q.where(Listing.listing_type == intent.listing_type)

    # Feature filters
    feature_field_map = {
        "parking":   Listing.has_parking,
        "graveyard": Listing.has_graveyard,
        "balcony":   Listing.has_balcony,
        "porch":     Listing.has_porch,
        "hall":      Listing.has_hall,
        "spire":     Listing.has_spire,
        "organ":     Listing.has_organ,
        "vestry":    Listing.has_vestry,
    }
    for feat in intent.features:
        field = feature_field_map.get(feat)
        if field is not None:
            q = q.where(field == True)

    # Charity distress scoring boost — order distressed properties higher
    # when intent includes conversion (likely motivated buyers)
    if tools.get("charity_scorer") and intent.intent_type == "buy_convert":
        if sort_by == "relevance":
            q = q.order_by(
                Listing.financial_distress_score.desc().nullslast(),
                Listing.first_seen.desc(),
            )

    # Planning signals — only include if relevant to intent
    if not tools.get("planning_lookup"):
        # Exclude pure planning signal listings from non-conversion searches
        q = q.where(
            ~Listing.source.ilike("%Planning Portal%")
        )

    # Sorting
    if sort_by == "price_asc":
        q = q.order_by(Listing.price_gbp.asc().nullslast())
    elif sort_by == "price_desc":
        q = q.order_by(Listing.price_gbp.desc().nullslast())
    elif sort_by == "date":
        q = q.order_by(Listing.first_seen.desc())
    elif sort_by == "relevance" and intent.intent_type != "buy_convert":
        q = q.order_by(Listing.first_seen.desc())

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar_one()

    # Paginate
    q    = q.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()

    return [_listing_to_dict(r) for r in rows], total


# ── Scoring ──────────────────────────────────────────────────────────────────

def _score_listing(listing: dict, intent: ParsedIntent) -> dict:
    """
    Pure Python match scoring. Returns listing with _score and _criteria.
    No LLM. Used for green/amber/grey chips on frontend.
    """
    criteria = []
    score_num = 0
    score_den = 0

    # Price match
    if intent.price_max:
        score_den += 2
        price = listing.get("price_gbp")
        if price and price <= intent.price_max:
            criteria.append({"label": f"Under £{intent.price_max//1000}k", "status": "exact", "detail": listing.get("price_raw","")})
            score_num += 2
        elif price and price <= intent.price_max * 1.15:
            criteria.append({"label": f"Near £{intent.price_max//1000}k", "status": "close", "detail": listing.get("price_raw","")})
            score_num += 1
        elif price:
            criteria.append({"label": f"Over £{intent.price_max//1000}k", "status": "miss", "detail": listing.get("price_raw","")})

    # Location match
    if intent.locations:
        score_den += 2
        loc    = (listing.get("location") or "").lower()
        county = (listing.get("county")   or "").lower()
        hit = any(
            l.lower() in loc or l.lower() in county
            for l in intent.locations
        )
        if hit:
            criteria.append({"label": intent.locations[0], "status": "exact"})
            score_num += 2
        else:
            criteria.append({"label": intent.locations[0], "status": "miss"})

    # Feature matches
    feat_map = {
        "parking": "has_parking", "graveyard": "has_graveyard",
        "balcony": "has_balcony", "porch":     "has_porch",
        "hall":    "has_hall",    "spire":      "has_spire",
        "organ":   "has_organ",   "vestry":     "has_vestry",
    }
    for feat in intent.features[:4]:
        score_den += 1
        field = feat_map.get(feat)
        has_it = field and listing.get(field)
        label  = feat.capitalize()
        if has_it:
            criteria.append({"label": label, "status": "exact"})
            score_num += 1
        else:
            criteria.append({"label": label, "status": "miss"})

    # Listing type
    if intent.listing_type not in ("any", ""):
        score_den += 1
        if listing.get("listing_type") == intent.listing_type:
            criteria.append({"label": intent.listing_type.capitalize(), "status": "exact"})
            score_num += 1
        else:
            criteria.append({"label": intent.listing_type.capitalize(), "status": "miss"})

    # Conversion intent vs AI score
    if intent.intent_type in ("buy_convert", "buy_preserve"):
        score_den += 1
        ai = listing.get("ai_score") or 0
        label = "Conversion potential" if intent.intent_type == "buy_convert" else "Heritage / preserve"
        if ai >= 7:
            criteria.append({"label": label, "status": "exact", "detail": f"AI: {ai}/10"})
            score_num += 1
        elif ai >= 4:
            criteria.append({"label": label, "status": "close", "detail": f"AI: {ai}/10"})
            score_num += 0.6

    # Calculate percentage
    pct = round((score_num / score_den) * 100) if score_den else 100

    # Distress signal boost (valuable signal even if partial match)
    dist = listing.get("financial_distress_score") or 0
    if dist >= 6:
        pct = min(100, pct + 5)

    listing["_score"]    = pct
    listing["_criteria"] = criteria[:6]
    return listing


# ── Broadening strategy ───────────────────────────────────────────────────────

def _can_broaden(intent: ParsedIntent) -> bool:
    return bool(
        intent.price_max or
        intent.locations or
        intent.features or
        intent.listing_type != "any"
    )

def _broaden_intent(intent: ParsedIntent) -> tuple[ParsedIntent, str]:
    """
    Drop the most restrictive constraint and explain why.
    Order: features first, then listing type, then price, then location.
    """
    import copy
    b = copy.copy(intent)

    if b.features:
        dropped = b.features.pop()
        return b, f"Relaxed feature filter ({dropped}) to find more results"

    if b.listing_type not in ("any", ""):
        b.listing_type = "any"
        return b, "Including all listing types (sale, auction, lease)"

    if b.price_max:
        new_max = int(b.price_max * 1.25)
        b.price_max = new_max
        return b, f"Expanded budget to £{new_max:,} to find more results"

    if b.locations:
        b.locations = []
        return b, "Searching across all UK locations"

    return b, "Broadened search criteria"


# ── Facets ───────────────────────────────────────────────────────────────────

async def _compute_facets(db: AsyncSession) -> dict:
    try:
        county_q = (
            select(Listing.county, func.count().label("count"))
            .where(Listing.is_active == True, Listing.county != "")
            .group_by(Listing.county)
            .order_by(func.count().desc())
            .limit(12)
        )
        source_q = (
            select(Listing.source, func.count().label("count"))
            .where(Listing.is_active == True)
            .group_by(Listing.source)
            .order_by(func.count().desc())
            .limit(15)
        )
        counties = (await db.execute(county_q)).all()
        sources  = (await db.execute(source_q)).all()
        return {
            "counties": [{"name": r[0] or "Unknown", "count": r[1]} for r in counties],
            "sources":  [{"name": r[0], "count": r[1]} for r in sources],
        }
    except Exception as exc:
        logger.warning("Facet computation failed: %s", exc)
        return {}


# ── LLM fallback ─────────────────────────────────────────────────────────────

async def _llm_intent_fallback(query: str, base: ParsedIntent) -> ParsedIntent:
    """
    Called only when deterministic confidence < 0.8.
    Uses the lightest possible model (not Claude Sonnet).
    Currently falls back to enhanced deterministic with lower threshold.
    Wire in Haiku/Gemma/Ollama here when ready.
    """
    logger.info("LLM fallback triggered for query: %s (conf=%.2f)", query, base.confidence)
    # For now: return the deterministic result with confidence bumped
    # In production: call Ollama mistral or Claude Haiku here
    base.confidence = 0.75
    return base


# ── Helpers ──────────────────────────────────────────────────────────────────

def _merge_filters(intent: ParsedIntent, filters: dict) -> ParsedIntent:
    if filters.get("price_max"):
        intent.price_max = int(filters["price_max"])
    if filters.get("price_min"):
        intent.price_min = int(filters["price_min"])
    if filters.get("counties"):
        intent.locations = filters["counties"]
    if filters.get("features"):
        for f in filters["features"]:
            if f not in intent.features:
                intent.features.append(f)
    if filters.get("listing_type") and filters["listing_type"] != "any":
        intent.listing_type = filters["listing_type"]
    if filters.get("intent"):
        intent.intent_type = filters["intent"]
    return intent


def _intent_to_dict(intent: ParsedIntent) -> dict:
    return {
        "intent_type":    intent.intent_type,
        "property_types": intent.property_types,
        "price_max":      intent.price_max,
        "price_min":      intent.price_min,
        "locations":      intent.locations,
        "features":       intent.features,
        "listing_type":   intent.listing_type,
        "urgency":        intent.urgency,
        "confidence":     intent.confidence,
        "is_relevant_query": intent.is_relevant,
        "keywords":       intent.keywords,
    }


def _listing_to_dict(listing: Listing) -> dict:
    return {
        "id":            listing.id,
        "source":        listing.source,
        "source_url":    listing.url,
        "title":         listing.title,
        "price_raw":     listing.price,
        "price_gbp":     listing.price_gbp if hasattr(listing, "price_gbp") else None,
        "location":      listing.location,
        "county":        listing.county    if hasattr(listing, "county")    else "",
        "postcode":      listing.postcode  if hasattr(listing, "postcode")  else "",
        "description":   listing.description,
        "listing_type":  listing.listing_type if hasattr(listing, "listing_type") else "sale",
        "has_parking":   listing.has_parking  if hasattr(listing, "has_parking")  else False,
        "has_graveyard": listing.has_graveyard if hasattr(listing, "has_graveyard") else False,
        "has_balcony":   listing.has_balcony  if hasattr(listing, "has_balcony")  else False,
        "has_porch":     listing.has_porch    if hasattr(listing, "has_porch")    else False,
        "has_hall":      listing.has_hall     if hasattr(listing, "has_hall")     else False,
        "has_spire":     listing.has_spire    if hasattr(listing, "has_spire")    else False,
        "has_organ":     listing.has_organ    if hasattr(listing, "has_organ")    else False,
        "has_vestry":    listing.has_vestry   if hasattr(listing, "has_vestry")   else False,
        "is_listed":     listing.is_listed    if hasattr(listing, "is_listed")    else False,
        "listed_grade":  listing.listed_grade if hasattr(listing, "listed_grade") else "",
        "in_conservation": listing.in_conservation if hasattr(listing, "in_conservation") else False,
        "heritage_at_risk": listing.heritage_at_risk if hasattr(listing, "heritage_at_risk") else False,
        "financial_distress_score": listing.financial_distress_score if hasattr(listing, "financial_distress_score") else 0,
        "dissolution_notice":  listing.dissolution_notice  if hasattr(listing, "dissolution_notice")  else False,
        "has_mortgage_charge": listing.has_mortgage_charge if hasattr(listing, "has_mortgage_charge") else False,
        "ai_score":      listing.ai_score  if hasattr(listing, "ai_score")  else None,
        "ai_uses":       listing.ai_uses   if hasattr(listing, "ai_uses")   else "[]",
        "ai_roi":        listing.ai_roi    if hasattr(listing, "ai_roi")    else "",
        "ai_risks":      listing.ai_risks  if hasattr(listing, "ai_risks")  else "[]",
        "ai_signal":     listing.ai_signal if hasattr(listing, "ai_signal") else "",
        "ai_summary":    listing.ai_summary if hasattr(listing, "ai_summary") else "",
        "is_off_market": listing.is_off_market if hasattr(listing, "is_off_market") else False,
        "first_seen":    listing.first_seen.isoformat(),
        "last_seen":     listing.last_seen.isoformat(),
        "image_url":     None,
        "_score":        100,
        "_criteria":     [],
    }
