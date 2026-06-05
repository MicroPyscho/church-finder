"""
Deterministic intent parser.
Parses user queries using regex, lookup tables, and the keyword
repository. LLM is only called when confidence < 0.8.

Architecture: parse_intent_deterministic → confidence check
              → LLM fallback only if needed (rare)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Compiled patterns (compiled once at import, O(1) per query) ─────────────

# Price patterns
_PRICE_PATTERNS = [
    (r'under\s*£?([\d,]+)\s*k',        lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'under\s*£?([\d,]+)\s*million',  lambda m: int(m.group(1).replace(",","")) * 1_000_000),
    (r'under\s*£?([\d,]+)',             lambda m: int(m.group(1).replace(",",""))),
    (r'below\s*£?([\d,]+)\s*k',        lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'less\s*than\s*£?([\d,]+)\s*k',  lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'max\s*£?([\d,]+)\s*k',          lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'budget\s*of\s*£?([\d,]+)\s*k',  lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'£?([\d,]+)\s*k\s*or\s*less',    lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'up\s*to\s*£?([\d,]+)\s*k',      lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'£([\d,]+)',                       lambda m: int(m.group(1).replace(",",""))),
    (r'([\d,]+)\s*k\b',                lambda m: int(m.group(1).replace(",","")) * 1000),
    (r'half\s*a?\s*million',            lambda m: 500_000),
    (r'a?\s*million',                   lambda m: 1_000_000),
]
_PRICE_RE = [(re.compile(p, re.IGNORECASE), fn) for p, fn in _PRICE_PATTERNS]

# UK counties and cities
_LOCATIONS = [
    "kent", "surrey", "sussex", "east sussex", "west sussex",
    "hampshire", "berkshire", "oxfordshire", "buckinghamshire",
    "hertfordshire", "essex", "suffolk", "norfolk", "cambridgeshire",
    "lincolnshire", "yorkshire", "north yorkshire", "south yorkshire",
    "west yorkshire", "lancashire", "gloucestershire", "wiltshire",
    "somerset", "devon", "dorset", "cornwall", "derbyshire",
    "nottinghamshire", "leicestershire", "staffordshire", "warwickshire",
    "northamptonshire", "shropshire", "herefordshire", "worcestershire",
    "cheshire", "cumbria", "durham", "northumberland",
    "scotland", "wales", "london", "manchester", "birmingham",
    "bristol", "liverpool", "leeds", "sheffield", "newcastle",
    "nottingham", "leicester", "coventry", "bradford", "edinburgh",
    "glasgow", "cardiff", "isle of wight",
]
_LOCATION_RE = re.compile(
    r'\b(' + '|'.join(re.escape(l) for l in sorted(_LOCATIONS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)

# Intent type signals
_INTENT_PATTERNS = {
    "buy_convert": [
        r'convert', r'conversion', r'residential conversion',
        r'change of use', r'develop', r'development potential',
        r'planning permission', r'prior approval', r'flats',
        r'apartments', r'commercial use', r'office', r'warehouse',
        r'mixed use', r'permitted development',
    ],
    "buy_preserve": [
        r'preserve', r'restoration', r'restore', r'heritage',
        r'listed building', r'grade i', r'grade ii', r'historic',
        r'conservation', r'protect', r'original features',
    ],
    "buy_religious": [
        r'mosque', r'temple', r'synagogue', r'gurdwara',
        r'non.?christian', r'multi.?faith', r'interfaith',
        r'prayer hall', r'islamic centre', r'hindu',
        r'sikh', r'jewish', r'buddhist',
    ],
    "buy_use": [
        r'use as (a )?church', r'use for (a )?church',
        r'congregation', r'worship service', r'sunday service',
        r'plant a church', r'start a church', r'open (a )?church',
        r'move (a )?church', r'relocate (a )?church',
        r'christian', r'evangelical', r'pentecostal', r'baptist use',
        r'methodist use', r'parish',
    ],
}
_INTENT_RE = {
    intent: [re.compile(p, re.IGNORECASE) for p in patterns]
    for intent, patterns in _INTENT_PATTERNS.items()
}

# Property type signals
_PROPERTY_TYPE_PATTERNS = {
    "church":      [r'church', r'chapel', r'ecclesiastical', r'vestry', r'nave', r'minster', r'abbey', r'priory', r'tabernacle', r'meeting house', r'place of worship'],
    "hall":        [r'village hall', r'community hall', r'assembly hall', r'masonic', r'memorial hall', r'drill hall', r'parish hall', r'social club', r'working men'],
    "large_space": [r'warehouse', r'mill', r'barn', r'theatre', r'cinema', r'former school', r'leisure centre', r'bingo hall', r'industrial'],
}
_PROPERTY_TYPE_RE = {
    pt: [re.compile(p, re.IGNORECASE) for p in patterns]
    for pt, patterns in _PROPERTY_TYPE_PATTERNS.items()
}

# Feature signals
_FEATURE_PATTERNS = {
    "parking":      [r'parking', r'car park', r'garage', r'driveway'],
    "graveyard":    [r'graveyard', r'churchyard', r'burial ground', r'cemetery'],
    "balcony":      [r'balcony', r'gallery', r'mezzanine'],
    "porch":        [r'porch', r'vestibule'],
    "hall":         [r'\bhall\b', r'parish hall', r'community hall'],
    "spire":        [r'spire', r'tower', r'bell tower', r'steeple'],
    "organ":        [r'organ', r'pipe organ'],
    "vestry":       [r'vestry', r'sacristy'],
    "high_ceiling": [r'high ceiling', r'clear span', r'vaulted'],
    "stage":        [r'stage', r'raised platform'],
    "kitchen":      [r'kitchen', r'catering'],
}
_FEATURE_RE = {
    feat: [re.compile(p, re.IGNORECASE) for p in patterns]
    for feat, patterns in _FEATURE_PATTERNS.items()
}

# Listing type signals
_AUCTION_RE   = re.compile(r'\bauction\b|\blot\b|\bguide price\b|\bbid\b|\bbidding\b', re.IGNORECASE)
_LEASE_RE     = re.compile(r'\blease\b|\brent\b|\bto let\b|\btenancy\b', re.IGNORECASE)

# Urgency signals
_URGENT_RE    = re.compile(r'\bsoon\b|\burgent\b|\bquickly\b|\bASAP\b|\bimmediately\b|\bthis (week|month)\b', re.IGNORECASE)
_AUCTION_SOON = re.compile(r'\bauction\b.{0,30}(this|next)\s+(week|month)|\b(upcoming|imminent)\s+auction\b', re.IGNORECASE)


# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class ParsedIntent:
    # Core
    intent_type:   str          = "explore"
    property_types: list[str]   = field(default_factory=lambda: ["church", "hall", "large_space"])
    keywords:      list[str]    = field(default_factory=list)

    # Filters
    price_max:     Optional[int] = None
    price_min:     Optional[int] = None
    locations:     list[str]    = field(default_factory=list)
    features:      list[str]    = field(default_factory=list)
    listing_type:  str          = "any"

    # Meta
    urgency:       str          = "flexible"
    confidence:    float        = 0.0
    is_relevant:   bool         = True
    raw_query:     str          = ""


# ── Main parser ──────────────────────────────────────────────────────────────

def parse_intent_deterministic(query: str) -> ParsedIntent:
    """
    Parse user query into structured intent using only regex and lookups.
    Returns confidence score — caller decides whether to invoke LLM fallback.
    """
    q       = query.strip()
    q_lower = q.lower()
    result  = ParsedIntent(raw_query=q)
    signals = 0   # count of signals found — drives confidence

    # ── 1. Relevance check ───────────────────────────────────────────────────
    from app.keywords import CORE_MATCH_KEYWORDS
    relevant = any(kw in q_lower for kw in CORE_MATCH_KEYWORDS)
    if not relevant:
        result.is_relevant = False
        result.confidence  = 0.95  # high confidence it's NOT relevant
        return result

    signals += 1

    # ── 2. Price ─────────────────────────────────────────────────────────────
    for pattern, extractor in _PRICE_RE:
        m = pattern.search(q)
        if m:
            try:
                val = extractor(m)
                if 10_000 <= val <= 50_000_000:  # sanity range
                    result.price_max = val
                    signals += 2
                    break
            except (ValueError, IndexError):
                pass

    # ── 3. Location ──────────────────────────────────────────────────────────
    locs = _LOCATION_RE.findall(q)
    if locs:
        result.locations = list(dict.fromkeys(l.title() for l in locs))
        signals += 2

    # ── 4. Intent type ───────────────────────────────────────────────────────
    intent_scores: dict[str, int] = {}
    for intent_type, patterns in _INTENT_RE.items():
        score = sum(1 for p in patterns if p.search(q))
        if score:
            intent_scores[intent_type] = score

    if intent_scores:
        result.intent_type = max(intent_scores, key=lambda k: intent_scores[k])
        signals += 2

    # ── 5. Property types ────────────────────────────────────────────────────
    found_types = []
    for pt, patterns in _PROPERTY_TYPE_RE.items():
        if any(p.search(q) for p in patterns):
            found_types.append(pt)
    if found_types:
        result.property_types = found_types
        signals += 1

    # ── 6. Features ──────────────────────────────────────────────────────────
    for feat, patterns in _FEATURE_RE.items():
        if any(p.search(q) for p in patterns):
            result.features.append(feat)
            signals += 1

    # ── 7. Listing type ──────────────────────────────────────────────────────
    if _AUCTION_RE.search(q):
        result.listing_type = "auction"
        signals += 1
    elif _LEASE_RE.search(q):
        result.listing_type = "lease"
        signals += 1

    # ── 8. Urgency ───────────────────────────────────────────────────────────
    if _AUCTION_SOON.search(q):
        result.urgency = "auction_soon"
    elif _URGENT_RE.search(q):
        result.urgency = "immediate"

    # ── 9. Keywords (remaining meaningful words for SQL LIKE search) ─────────
    stopwords = {
        "a", "an", "the", "in", "on", "at", "for", "with", "and", "or",
        "to", "of", "is", "are", "i", "me", "my", "want", "need", "looking",
        "find", "search", "show", "get", "give", "some", "any", "all",
        "please", "can", "could", "would", "like", "most", "very",
        "affordable", "cheap", "good", "nice", "large", "big", "small",
    }
    words = re.findall(r'\b[a-z]{3,}\b', q_lower)
    result.keywords = [w for w in words if w not in stopwords][:8]

    # ── 10. Confidence calculation ───────────────────────────────────────────
    # Base confidence from signal count
    # 0 signals = 0.3, 3 signals = 0.7, 6+ signals = 0.95
    base = min(0.95, 0.3 + (signals * 0.11))

    # Boost if we have price + location (very specific query)
    if result.price_max and result.locations:
        base = min(0.98, base + 0.1)

    # Penalise if query is very short (less reliable)
    if len(q.split()) <= 2:
        base = max(0.3, base - 0.2)

    result.confidence = round(base, 2)

    logger.debug(
        "Intent parsed: type=%s price=%s locs=%s feats=%s conf=%.2f",
        result.intent_type, result.price_max,
        result.locations, result.features, result.confidence,
    )

    return result


# ── Tool planner ─────────────────────────────────────────────────────────────

def plan_tools(intent: ParsedIntent) -> dict[str, bool]:
    """
    Pure if/else — decides which search tools to activate.
    Zero LLM. Returns a dict of tool flags.
    """
    return {
        "sql_filter":      True,                              # always
        "text_search":     bool(intent.keywords),             # if keywords present
        "charity_scorer":  True,                              # always — distress signals
        "planning_lookup": "convert" in intent.intent_type or
                           "preserve" in intent.intent_type,  # only for conversion intent
        "auction_filter":  intent.listing_type == "auction",  # auction queries only
        "heritage_filter": intent.intent_type == "buy_preserve",
    }
