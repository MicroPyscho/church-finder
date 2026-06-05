"""
Keyword repository for Sanctuary.
Used by the intent parser for relevance checking.
"""

CORE_MATCH_KEYWORDS = [
    # Churches & religious buildings
    "church", "chapel", "ecclesiastical", "vestry", "nave",
    "place of worship", "religious building", "tabernacle",
    "congregation", "parish", "minster", "priory", "abbey",
    "meeting house", "mission hall", "redundant church",
    "former church", "decommissioned", "methodist", "baptist",
    "anglican", "catholic", "quaker", "salvation army",
    "kingdom hall", "united reformed", "gospel hall",
    "evangelical", "pentecostal", "christian", "diocese",
    # Halls & community buildings
    "village hall", "community hall", "assembly hall",
    "masonic hall", "memorial hall", "working men",
    "social club", "drill hall", "civic hall", "parish hall",
    "function hall", "banqueting hall", "lecture hall",
    "institute building", "mechanics institute",
    # Large spaces
    "warehouse conversion", "mill building", "barn conversion",
    "former theatre", "former cinema", "bingo hall",
    "former school", "leisure centre", "sports hall",
    # Planning & distress signals
    "change of use", "d1", "f1 use class",
    "listed building", "conservation area",
    "surplus property", "disposal", "diocese disposal",
    "charity dissolution", "mortgagee", "receiver sale",
    "development potential", "planning permission",
    # Physical features
    "graveyard", "churchyard", "burial ground",
    "high ceiling", "clear span", "auditorium",
    "tiered seating", "spire", "tower", "bell tower",
    "steeple", "organ", "pipe organ", "porch", "vestry",
]

def matches_keywords(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in CORE_MATCH_KEYWORDS)
