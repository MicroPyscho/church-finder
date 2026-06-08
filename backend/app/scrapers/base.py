"""
Base classes and utilities shared by all scrapers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import hashlib
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ScrapedListing:
    """Represents a single property listing found by a scraper."""
    source:        str
    url:           str
    title:         str
    price_raw:     str           = "POA"
    location:      str           = ""
    county:        str           = ""
    postcode:      str           = ""
    description:   str           = ""
    property_type: str           = "other"
    listing_type:  str           = "sale"   # sale | let | auction
    image_url:     Optional[str] = None
    images_json:   list          = field(default_factory=list)
    is_signal:     bool          = False
    signal_type:   str           = ""

    @property
    def id(self) -> str:
        """Stable unique ID based on source + URL."""
        return hashlib.md5(f"{self.source}:{self.url}".encode()).hexdigest()

    def is_valid(self) -> bool:
        """Must have title + URL, or title + location."""
        has_title    = bool(self.title and len(self.title.strip()) > 5)
        has_url      = bool(self.url and self.url.startswith("http"))
        has_location = bool(self.location and len(self.location.strip()) > 2)
        return sum([has_title, has_url, has_location]) >= 2


# ── Keyword lists ──────────────────────────────────────────────────────────

CHURCH_KEYWORDS = [
    # Core
    "church", "churches", "chapel", "chapels", "ecclesiastical",
    "place of worship", "places of worship",
    "nave", "vestry", "tabernacle", "minster", "priory", "abbey", "cathedral",
    "meeting house", "mission hall", "former church", "redundant church",
    # Building types
    "gospel hall", "kingdom hall", "bethel", "bethesda", "ebenezer",
    "church hall", "church auditorium", "church building",
    "village hall", "community hall", "assembly hall", "masonic hall",
    "memorial hall", "drill hall", "civic hall", "parish hall",
    "local church", "religious building", "place of gathering",
    "citadel", "zion chapel", "temperance hall",
    # Denominations
    "methodist", "baptist", "evangelical", "pentecostal",
    "united reformed", "salvation army", "quaker", "anglican",
    "presbyterian", "congregational", "wesleyan", "free church",
    "brethren", "urc", "reformed",
    # Conversions
    "converted chapel", "converted church", "church conversion",
    "former chapel", "former cathedral", "redundant chapel",
    "former place of worship",
    # Admin
    "diocese", "parish", "congregation", "sanctuary",
]

# Patterns where "church" appears in a street name, not a building
FALSE_POSITIVE_RE = re.compile(
    r'church\s+(?:street|road|lane|avenue|close|drive|way|place|court|terrace|'
    r'end|hill|view|farm|gate|yard|walk|row|grove|crescent|mews|square|'
    r'path|rise|park|green|meadow|field|gardens|buildings|house|cottages|'
    r'mount|bank|bridge|side|wharf|quay)\b'
    r'|charles\s+church'
    r'|church\s+&\s+\w+'
    r'|\d+\s+church\s+(?:street|road|lane|avenue)',
    re.IGNORECASE,
)

ARTICLE_SIGNALS = [
    "article page", "visit reports", "windrush generation",
    "passivhaus", "urgent fabric", "open doors project",
    "faith in the future", "why are historic",
]


def is_genuine_church(title: str, description: str = "") -> bool:
    """Return True if this text describes a real church/chapel property."""
    combined    = (title + " " + description).lower()
    title_lower = title.lower()

    if not any(kw in combined for kw in CHURCH_KEYWORDS):
        return False
    if any(sig in combined for sig in ARTICLE_SIGNALS):
        return False
    if "church" in title_lower:
        cleaned = FALSE_POSITIVE_RE.sub("", title_lower)
        if "church" not in cleaned and not any(
            kw in cleaned for kw in CHURCH_KEYWORDS if kw != "church"
        ):
            desc_lower = description.lower()
            if not any(kw in desc_lower for kw in [
                "chapel", "ecclesiastical", "place of worship", "worship",
                "congregation", "former church", "nave", "vestry",
            ]):
                return False
    return True


def classify(text: str) -> str:
    """Classify property type from text."""
    t = text.lower()
    if any(k in t for k in [
        "church", "chapel", "ecclesiastical", "vestry", "tabernacle",
        "place of worship", "gospel hall", "meeting house", "nave",
        "minster", "priory", "abbey", "cathedral", "auditorium",
        "religious building",
    ]):
        return "church"
    if any(k in t for k in [
        "village hall", "community hall", "masonic", "memorial hall",
        "drill hall", "parish hall", "church hall", "assembly hall",
        "civic hall", "place of gathering",
    ]):
        return "hall"
    if any(k in t for k in [
        "warehouse", "mill", "theatre", "cinema", "bingo hall",
        "former school", "barn",
    ]):
        return "large_space"
    return "other"


def extract_price(text: str) -> str:
    """Extract first price mention from text."""
    m = re.search(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?', text)
    return m.group(0) if m else ""


def clean_text(raw: str) -> str:
    """Remove markdown, HTML entities, and other junk from scraped text."""
    if not raw:
        return raw
    t = raw
    t = re.sub(r'^#{1,6}\s+', '', t, flags=re.MULTILINE)
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
    t = re.sub(r'\*([^*]+)\*', r'\1', t)
    t = re.sub(r'\[[^\]]*\]', '', t)
    t = t.replace('&amp;', '&').replace('&nbsp;', ' ')
    t = t.replace('\u00a0', ' ').replace('\u200b', '')
    t = t.replace('\u2019', "'").replace('\u2013', '-').replace('\u2014', '-')
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = ' '.join(line.strip() for line in t.split('\n') if line.strip())
    return t.strip()


# ── Base scraper class ─────────────────────────────────────────────────────

class BaseScraper(ABC):
    """
    Abstract base for all scrapers.

    Subclasses must implement scrape(client) and set source_name.
    source_type is either 'httpx' (default) or 'playwright'.
    """
    source_name: str = ""
    source_type: str = "httpx"

    def __init__(self):
        self.logger = logging.getLogger(f"scrapers.{self.__class__.__name__}")

    @abstractmethod
    async def scrape(self, client) -> list[ScrapedListing]:
        """
        Scrape listings from this source.
        client: httpx.AsyncClient for httpx scrapers,
                playwright.Page for playwright scrapers.
        """
        ...

    def make_listing(self, **kwargs) -> ScrapedListing:
        """Create a ScrapedListing with this scraper's source_name."""
        return ScrapedListing(source=self.source_name, **kwargs)

    def log_result(self, count: int) -> None:
        self.logger.info("%s: %d listings found", self.source_name, count)
