"""
Location intelligence for Sanctuary search.

Maps UK regions to postcode prefixes and neighbouring regions.
Enables proximity-aware search: exact match first, then near matches.

Structure:
  REGION_POSTCODES  — region name → list of postcode prefixes
  REGION_NEIGHBOURS — region name → ordered list of neighbouring regions
  POSTCODE_REGION   — postcode prefix → region name (reverse lookup)
"""

# ── Region → postcode prefix mapping ─────────────────────────────────────

REGION_POSTCODES: dict[str, list[str]] = {
    # London
    "Central London":    ["EC", "WC"],
    "North London":      ["N", "NW"],
    "East London":       ["E"],
    "South London":      ["SE", "SW"],
    "West London":       ["W", "WC"],
    "Greater London":    ["IG", "RM", "DA", "BR", "CR", "SM", "KT",
                          "TW", "UB", "HA", "EN", "WD", "E", "N",
                          "NW", "SE", "SW", "W", "EC", "WC"],
    # South East
    "Kent":              ["CT", "ME", "TN", "DA"],
    "Surrey":            ["GU", "KT", "RH", "SM", "CR", "TW"],
    "Sussex":            ["BN", "RH", "TN"],
    "East Sussex":       ["BN", "TN"],
    "West Sussex":       ["BN", "RH", "PO"],
    "Hampshire":         ["PO", "SO", "GU", "RG", "SP"],
    "Berkshire":         ["RG", "SL", "GU"],
    "Hertfordshire":     ["AL", "EN", "HP", "SG", "WD"],
    "Essex":             ["CM", "CO", "IG", "RM", "SS"],
    "Buckinghamshire":   ["HP", "MK", "SL"],
    "Oxfordshire":       ["OX"],
    # South West
    "Devon":             ["EX", "PL", "TQ"],
    "Cornwall":          ["PL", "TR"],
    "Somerset":          ["BA", "BS", "TA"],
    "Dorset":            ["BH", "DT", "SP"],
    "Wiltshire":         ["BA", "SN", "SP"],
    "Gloucestershire":   ["GL"],
    "Bristol":           ["BS"],
    # Midlands
    "West Midlands":     ["B", "CV", "DY", "WS", "WV"],
    "Warwickshire":      ["CV", "B"],
    "Staffordshire":     ["ST", "WS", "WV"],
    "Leicestershire":    ["LE"],
    "Nottinghamshire":   ["NG"],
    "Derbyshire":        ["DE", "NG", "S"],
    "Northamptonshire":  ["NN"],
    "Worcestershire":    ["WR", "DY"],
    "Shropshire":        ["SY", "TF"],
    "Herefordshire":     ["HR"],
    "Lincolnshire":      ["LN", "DN", "NG", "PE"],
    # East
    "Norfolk":           ["NR"],
    "Suffolk":           ["CO", "IP"],
    "Cambridgeshire":    ["CB", "PE"],
    # North West
    "Lancashire":        ["BB", "FY", "LA", "PR"],
    "Cheshire":          ["CH", "CW", "SK", "WA"],
    "Manchester":        ["M", "SK", "BL", "OL", "WN"],
    "Merseyside":        ["L", "CH", "WA", "PR"],
    "Cumbria":           ["CA", "LA"],
    # Yorkshire
    "West Yorkshire":    ["BD", "HD", "HX", "LS", "WF"],
    "South Yorkshire":   ["DN", "S"],
    "North Yorkshire":   ["DL", "HG", "TS", "YO"],
    "East Yorkshire":    ["HU", "YO"],
    "Yorkshire":         ["BD", "DN", "HD", "HG", "HX", "HU",
                          "LS", "S", "WF", "YO"],
    # North East
    "Durham":            ["DH", "DL", "SR"],
    "Northumberland":    ["NE"],
    "Tyne and Wear":     ["NE", "SR"],
    # Wales
    "Wales":             ["CF", "LD", "LL", "NP", "SA", "SY"],
    "Cardiff":           ["CF"],
    "Swansea":           ["SA"],
    # Scotland
    "Scotland":          ["AB", "DD", "DG", "EH", "FK", "G",
                          "HS", "IV", "KA", "KW", "KY", "ML",
                          "PA", "PH", "TD", "ZE"],
    "Edinburgh":         ["EH"],
    "Glasgow":           ["G", "ML", "PA"],
}

# ── Reverse lookup: postcode prefix → primary region ─────────────────────

POSTCODE_REGION: dict[str, str] = {}
for region, prefixes in REGION_POSTCODES.items():
    for prefix in prefixes:
        if prefix not in POSTCODE_REGION:
            POSTCODE_REGION[prefix] = region

# ── Regional proximity graph ──────────────────────────────────────────────
# Each region lists neighbours in order of proximity (closest first)

REGION_NEIGHBOURS: dict[str, list[str]] = {
    "Greater London":  ["Kent", "Surrey", "Essex", "Hertfordshire",
                        "Berkshire", "Buckinghamshire", "Sussex"],
    "Central London":  ["Greater London", "Kent", "Surrey", "Essex"],
    "Kent":            ["Greater London", "Surrey", "Sussex", "Essex"],
    "Surrey":          ["Greater London", "Kent", "Sussex", "Hampshire", "Berkshire"],
    "Sussex":          ["Surrey", "Kent", "Hampshire"],
    "Hampshire":       ["Surrey", "Sussex", "Wiltshire", "Berkshire", "Dorset"],
    "Berkshire":       ["Greater London", "Surrey", "Hampshire", "Oxfordshire", "Buckinghamshire"],
    "Essex":           ["Greater London", "Kent", "Suffolk", "Hertfordshire", "Cambridgeshire"],
    "Hertfordshire":   ["Greater London", "Essex", "Bedfordshire", "Buckinghamshire"],
    "Oxfordshire":     ["Berkshire", "Buckinghamshire", "Gloucestershire", "Northamptonshire"],
    "Yorkshire":       ["Lancashire", "Durham", "Nottinghamshire", "Lincolnshire", "Derbyshire"],
    "West Yorkshire":  ["South Yorkshire", "Lancashire", "North Yorkshire"],
    "South Yorkshire": ["West Yorkshire", "Derbyshire", "Nottinghamshire", "Lincolnshire"],
    "North Yorkshire": ["West Yorkshire", "Durham", "Lancashire", "East Yorkshire"],
    "Lancashire":      ["West Yorkshire", "Cheshire", "Cumbria", "Manchester"],
    "Manchester":      ["Lancashire", "Cheshire", "West Yorkshire"],
    "West Midlands":   ["Staffordshire", "Warwickshire", "Worcestershire", "Shropshire"],
    "Warwickshire":    ["West Midlands", "Northamptonshire", "Leicestershire"],
    "Nottinghamshire": ["Derbyshire", "Lincolnshire", "South Yorkshire", "Leicestershire"],
    "Wales":           ["Shropshire", "Herefordshire", "Gloucestershire", "Cheshire"],
    "Scotland":        ["Northumberland", "Durham", "Cumbria"],
    "Devon":           ["Somerset", "Cornwall", "Dorset"],
    "Cornwall":        ["Devon"],
    "Somerset":        ["Devon", "Dorset", "Wiltshire", "Gloucestershire", "Bristol"],
}


# ── Simple aliases — common names that map to canonical regions ──────────
ALIASES: dict[str, str] = {
    "london":        "Greater London",
    "birmingham":    "West Midlands",
    "manchester":    "Manchester",
    "yorkshire":     "Yorkshire",
    "wales":         "Wales",
    "scotland":      "Scotland",
    "midlands":      "West Midlands",
    "northwest":     "Lancashire",
    "northeast":     "Durham",
    "southwest":     "Devon",
    "southeast":     "Kent",
    "north":         "Yorkshire",
    "south":         "Surrey",
    "east":          "Essex",
    "west":          "Devon",
    "kent":          "Kent",
    "surrey":        "Surrey",
    "essex":         "Essex",
    "sussex":        "Sussex",
    "hampshire":     "Hampshire",
    "devon":         "Devon",
    "cornwall":      "Cornwall",
    "somerset":      "Somerset",
    "dorset":        "Dorset",
    "wiltshire":     "Wiltshire",
    "oxfordshire":   "Oxfordshire",
    "berkshire":     "Berkshire",
    "hertfordshire": "Hertfordshire",
    "buckinghamshire":"Buckinghamshire",
    "suffolk":       "Suffolk",
    "norfolk":       "Norfolk",
    "lincolnshire":  "Lincolnshire",
    "nottinghamshire":"Nottinghamshire",
    "derbyshire":    "Derbyshire",
    "leicestershire":"Leicestershire",
    "warwickshire":  "Warwickshire",
    "staffordshire": "Staffordshire",
    "shropshire":    "Shropshire",
    "worcestershire":"Worcestershire",
    "lancashire":    "Lancashire",
    "cheshire":      "Cheshire",
    "cumbria":       "Cumbria",
    "durham":        "Durham",
    "northumberland":"Northumberland",
}


def get_search_regions(query: str) -> dict[str, list[str]]:
    """
    Extract locations from query and return tiered search regions.

    Returns:
        {
          "exact":  [...],   # exact match regions — score boost
          "near":   [...],   # neighbouring regions — partial score
          "wider":  [...],   # wider area — shown if exact/near empty
        }

    If no location mentioned: returns empty dict (search all listings).
    """
    q = query.lower()
    words = set(q.split())

    # Find mentioned locations using aliases first, then full region names
    mentioned = []
    seen = set()

    # Check aliases (handles "london", "yorkshire" etc)
    for alias, canonical in ALIASES.items():
        if alias in words and canonical not in seen:
            mentioned.append(canonical)
            seen.add(canonical)

    # Also check full region names
    for region in REGION_POSTCODES:
        r = region.lower()
        if r in words and region not in seen:
            mentioned.append(region)
            seen.add(region)

    # Also detect postcode fragments (e.g. "IG6", "SW1")
    import re
    postcode_matches = re.findall(r'\b([A-Z]{1,2}\d{1,2})\b', query.upper())
    for pc in postcode_matches:
        # Match prefix
        for prefix_len in [2, 1]:
            prefix = pc[:prefix_len]
            if prefix in POSTCODE_REGION:
                region = POSTCODE_REGION[prefix]
                if region not in mentioned:
                    mentioned.append(region)
                break

    if not mentioned:
        return {}

    exact = list(mentioned)
    near = []
    wider = []

    for region in mentioned:
        neighbours = REGION_NEIGHBOURS.get(region, [])
        for n in neighbours[:4]:
            if n not in exact and n not in near:
                near.append(n)
        for n in neighbours[4:]:
            if n not in exact and n not in near and n not in wider:
                wider.append(n)

    # Get all postcode prefixes for each tier
    def to_terms(regions: list[str]) -> list[str]:
        terms = set()
        for r in regions:
            terms.add(r)
            for pc in REGION_POSTCODES.get(r, []):
                terms.add(pc)
        return list(terms)

    return {
        "exact":  to_terms(exact),
        "near":   to_terms(near),
        "wider":  to_terms(wider),
        "regions": exact,
    }
