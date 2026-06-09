"""
Location tier system for Sanctuary search.

Defines geographic proximity clusters for UK regions.
Each location has: exact terms, near terms, wider terms.

Used to build tiered search: exact match first, then near, then wider.
This ensures we always return results even when DB has sparse coverage.
"""

# Each region: [exact_terms, near_terms, wider_terms]
# Terms are matched against the location field using ilike
# Include: place names, postcode prefixes, county names, borough names

LOCATION_TIERS: dict[str, dict] = {

    "london": {
        "exact": [
            # Inner London postcodes and boroughs
            "EC", "WC", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9",
            "E10", "E11", "E12", "E13", "E14", "E15", "E16", "E17",
            "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N10",
            "NW1", "NW2", "NW3", "NW5", "NW6", "NW8", "NW10",
            "SE1", "SE4", "SE5", "SE6", "SE7", "SE8", "SE10", "SE11",
            "SE13", "SE14", "SE15", "SE16", "SE17", "SE18", "SE22", "SE24",
            "SW1", "SW2", "SW3", "SW4", "SW6", "SW8", "SW9", "SW10", "SW11",
            "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11",
            # Greater London area postcodes
            "IG", "RM", "DA", "BR", "CR", "SM", "KT", "TW", "UB", "HA", "EN", "WD",
            # Place names
            "London", "Hackney", "Croydon", "Greenwich", "Woolwich", "Bromley",
            "Clerkenwell", "Hammersmith", "Fulham", "Barkingside", "Chingford",
            "Sidcup", "Islington", "Lambeth", "Southwark", "Newham", "Barking",
            "Havering", "Redbridge", "Waltham", "Enfield", "Barnet", "Haringey",
            "Camden", "Westminster", "Kensington", "Chelsea", "Wandsworth",
            "Merton", "Sutton", "Kingston", "Richmond", "Hounslow", "Ealing",
            "Hillingdon", "Harrow", "Brent", "Tower Hamlets", "Lewisham",
        ],
        "near": [
            # Home Counties
            "Kent", "Surrey", "Essex", "Hertfordshire", "Berkshire",
            "Buckinghamshire", "Oxfordshire",
            "CT", "ME", "TN", "GU", "RH", "CM", "CO", "SS", "AL", "SG",
            "HP", "RG", "SL", "OX",
            "Maidstone", "Canterbury", "Guildford", "Chelmsford", "Watford",
            "Reading", "Oxford", "Aylesbury", "St Albans",
        ],
        "wider": [
            "Hampshire", "Sussex", "Suffolk", "Cambridgeshire", "Northamptonshire",
            "PO", "SO", "BN", "IP", "CB", "NN",
            "Southampton", "Brighton", "Ipswich", "Cambridge", "Northampton",
        ],
    },

    "yorkshire": {
        "exact": [
            "Yorkshire", "BD", "DN", "HD", "HG", "HX", "HU", "LS", "WF", "YO",
            "Barnsley", "Leeds", "Sheffield", "Bradford", "Hull", "York",
            "Harrogate", "Wakefield", "Doncaster", "Huddersfield", "Halifax",
            "Rotherham", "Scarborough", "Middlesbrough", "Beverley",
        ],
        "near": [
            "Lancashire", "Durham", "Lincolnshire", "Nottinghamshire", "Derbyshire",
            "BB", "FY", "PR", "DH", "DL", "LN", "NG", "DE", "S",
            "Burnley", "Preston", "Sunderland", "Lincoln", "Nottingham", "Derby",
        ],
        "wider": [
            "Cheshire", "Staffordshire", "Leicestershire", "Northumberland",
            "CH", "CW", "ST", "LE", "NE",
            "Chester", "Stoke", "Leicester", "Newcastle",
        ],
    },

    "kent": {
        "exact": [
            "Kent", "CT", "ME", "TN", "DA",
            "Maidstone", "Canterbury", "Rochester", "Chatham", "Gravesend",
            "Tonbridge", "Tunbridge Wells", "Folkestone", "Dover", "Margate",
            "Ramsgate", "Ashford", "Sevenoaks", "Sittingbourne", "Swanscombe",
        ],
        "near": [
            "Surrey", "Sussex", "Essex",
            "GU", "RH", "BN", "CM", "SS",
            "Guildford", "Brighton", "Chelmsford",
        ],
        "wider": [
            "London", "Hampshire",
            "SE", "SW", "PO", "SO",
        ],
    },

    "surrey": {
        "exact": [
            "Surrey", "GU", "KT", "RH", "SM", "CR", "TW",
            "Guildford", "Woking", "Epsom", "Reigate", "Dorking",
            "Farnham", "Camberley", "Staines", "Kingston", "Sutton",
        ],
        "near": [
            "Kent", "Sussex", "Hampshire", "Berkshire",
            "CT", "ME", "BN", "PO", "RG", "SL",
            "Maidstone", "Brighton", "Southampton", "Reading",
        ],
        "wider": ["London", "Oxfordshire", "SE", "SW", "OX"],
    },

    "manchester": {
        "exact": [
            "Manchester", "M", "SK", "BL", "OL", "WN",
            "Salford", "Stockport", "Oldham", "Bolton", "Wigan",
            "Rochdale", "Bury", "Trafford", "Tameside",
        ],
        "near": [
            "Lancashire", "Cheshire", "Yorkshire",
            "BB", "FY", "PR", "CH", "CW", "WA",
            "Blackburn", "Preston", "Chester", "Warrington",
        ],
        "wider": ["Derbyshire", "Staffordshire", "DE", "ST"],
    },

    "midlands": {
        "exact": [
            "Midlands", "Birmingham", "B", "CV", "DY", "WS", "WV",
            "Coventry", "Wolverhampton", "Dudley", "Walsall", "Solihull",
            "West Midlands",
        ],
        "near": [
            "Worcestershire", "Warwickshire", "Staffordshire", "Leicestershire",
            "WR", "DE", "LE", "NG",
            "Worcester", "Derby", "Leicester", "Nottingham",
        ],
        "wider": [
            "Shropshire", "Herefordshire", "Northamptonshire",
            "SY", "HR", "NN",
        ],
    },

    "wales": {
        "exact": [
            "Wales", "CF", "LD", "LL", "NP", "SA", "SY",
            "Cardiff", "Swansea", "Newport", "Wrexham", "Bangor",
            "Aberystwyth", "Carmarthen", "Llandudno",
        ],
        "near": [
            "Shropshire", "Herefordshire", "Cheshire", "Gloucestershire",
            "SY", "HR", "CH", "GL",
            "Shrewsbury", "Hereford", "Chester", "Gloucester",
        ],
        "wider": ["West Midlands", "B", "Birmingham"],
    },

    "scotland": {
        "exact": [
            "Scotland", "EH", "G", "AB", "DD", "KY", "PH", "PA", "ML",
            "Edinburgh", "Glasgow", "Aberdeen", "Dundee", "Stirling",
            "Perth", "Inverness", "St Andrews",
        ],
        "near": [
            "Northumberland", "Durham", "Cumbria",
            "NE", "DH", "CA",
            "Newcastle", "Carlisle",
        ],
        "wider": ["Yorkshire", "Lancashire", "BD", "BB"],
    },

    "devon": {
        "exact": [
            "Devon", "EX", "PL", "TQ",
            "Exeter", "Plymouth", "Torquay", "Paignton", "Barnstaple",
        ],
        "near": [
            "Cornwall", "Somerset", "Dorset",
            "TR", "BA", "TA", "BH", "DT",
            "Truro", "Bath", "Taunton", "Bournemouth",
        ],
        "wider": ["Wiltshire", "Gloucestershire", "SN", "GL"],
    },

    "cornwall": {
        "exact": ["Cornwall", "TR", "PL", "Truro", "Penzance", "Falmouth", "St Ives"],
        "near": ["Devon", "EX", "TQ", "Exeter", "Plymouth"],
        "wider": ["Somerset", "BA", "TA"],
    },
}

# Aliases — alternative names users might type
ALIASES: dict[str, str] = {
    "london":          "london",
    "greater london":  "london",
    "yorkshire":       "yorkshire",
    "north yorkshire": "yorkshire",
    "south yorkshire": "yorkshire",
    "west yorkshire":  "yorkshire",
    "east yorkshire":  "yorkshire",
    "kent":            "kent",
    "surrey":          "surrey",
    "manchester":      "manchester",
    "greater manchester": "manchester",
    "midlands":        "midlands",
    "west midlands":   "midlands",
    "east midlands":   "midlands",
    "birmingham":      "midlands",
    "wales":           "wales",
    "scotland":        "scotland",
    "devon":           "devon",
    "cornwall":        "cornwall",
    # Cities that map to regions
    "leeds":           "yorkshire",
    "sheffield":       "yorkshire",
    "bradford":        "yorkshire",
    "hull":            "yorkshire",
    "york":            "yorkshire",
    "barnsley":        "yorkshire",
    "doncaster":       "yorkshire",
    "maidstone":       "kent",
    "canterbury":      "kent",
    "rochester":       "kent",
    "guildford":       "surrey",
    "woking":          "surrey",
    "salford":         "manchester",
    "stockport":       "manchester",
    "coventry":        "midlands",
    "wolverhampton":   "midlands",
    "cardiff":         "wales",
    "swansea":         "wales",
    "edinburgh":       "scotland",
    "glasgow":         "scotland",
    "exeter":          "devon",
    "plymouth":        "devon",
}


def detect_location(query: str) -> str | None:
    """Detect the primary location mentioned in a query. Returns canonical key."""
    q = query.lower()
    words = set(q.split())

    # Check aliases first (single words)
    for alias, canonical in ALIASES.items():
        if alias in words or alias in q:
            return canonical

    return None


def get_tiers(query: str) -> dict | None:
    """
    Get tiered search terms for the location mentioned in query.
    Returns None if no location detected.
    """
    canonical = detect_location(query)
    if not canonical:
        return None
    return LOCATION_TIERS.get(canonical)
