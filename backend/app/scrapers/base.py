from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import hashlib
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ScrapedListing:
    source:        str
    url:           str
    title:         str
    price_raw:     str           = "POA"
    location:      str           = ""
    county:        str           = ""
    postcode:      str           = ""
    description:   str           = ""
    property_type: str           = "other"
    listing_type:  str           = "sale"
    image_url:     Optional[str] = None
    images_json:   list          = field(default_factory=list)
    is_signal:     bool          = False
    signal_type:   str           = ""

    @property
    def id(self) -> str:
        return hashlib.md5(f"{self.source}:{self.url}".encode()).hexdigest()

    def is_valid(self) -> bool:
        has_title    = bool(self.title and len(self.title.strip()) > 5)
        has_url      = bool(self.url and self.url.startswith("http"))
        has_location = bool(self.location and len(self.location.strip()) > 2)
        return sum([has_title, has_url, has_location]) >= 2


# All keywords that indicate a genuine church/worship property
CHURCH_KEYWORDS = [
    # Core terms
    "church", "churches", "chapel", "chapels", "ecclesiastical",
    "vestry", "nave", "place of worship", "places of worship",
    "tabernacle", "minster", "priory", "abbey", "cathedral",
    "meeting house", "mission hall", "former church", "redundant church",
    # Specific building types
    "gospel hall", "kingdom hall", "bethel", "bethesda", "ebenezer",
    "zion chapel", "memorial hall", "temperance hall", "citadel",
    "village hall", "community hall", "assembly hall", "masonic hall",
    "church hall", "church auditorium", "church building",
    "memorial hall", "drill hall", "civic hall", "parish hall",
    "local church", "religious building", "place of gathering",
    # Denominations
    "methodist", "baptist", "gospel", "evangelical", "pentecostal",
    "united reformed", "salvation army", "quaker", "anglican",
    "presbyterian", "congregational", "wesleyan", "primitive methodist",
    "free church", "brethren hall", "urc", "reformed",
    # Conversion terms
    "converted chapel", "converted church", "church conversion",
    "former chapel", "former cathedral", "redundant chapel",
    "former place of worship", "former religious",
    # Diocese/admin
    "diocese", "parish", "congregation", "vestry", "presbytery",
]

FALSE_POSITIVE_RE = re.compile(
    r'church\s+(?:street|road|lane|avenue|close|drive|way|place|court|terrace|'
    r'end|hill|view|farm|gate|yard|walk|row|grove|crescent|mews|square|'
    r'path|rise|park|green|meadow|field|gardens|buildings|house|cottages|'
    r'mount|bank|bridge|side|wharf|quay)\b'
    r'|charles\s+church'
    r'|church\s+&\s+\w+'
    r'|\d+\s+church\s+(?:street|road|lane|avenue)'
    r'|bocking\s+church\s+street'
    r'|church\s+farm\s+lane',
    re.IGNORECASE,
)

ARTICLE_SIGNALS = [
    "article page", "visit reports", "auspicious moments",
    "windrush generation", "passivhaus", "urgent fabric",
    "open doors project", "faith in the future", "why are historic",
]


def is_genuine_church(title: str, description: str = "") -> bool:
    combined   = (title + " " + description).lower()
    title_lower = title.lower()

    if not any(kw in combined for kw in CHURCH_KEYWORDS):
        return False
    if any(sig in combined for sig in ARTICLE_SIGNALS):
        return False
    if "church" in title_lower:
        title_cleaned = FALSE_POSITIVE_RE.sub("", title_lower)
        if "church" not in title_cleaned and not any(
            kw in title_cleaned for kw in CHURCH_KEYWORDS if kw != "church"
        ):
            desc_lower = description.lower()
            redeeming = any(kw in desc_lower for kw in [
                "chapel", "ecclesiastical", "place of worship", "worship",
                "congregation", "former church", "nave", "vestry",
            ])
            if not redeeming:
                return False
    return True


def classify(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["church", "chapel", "ecclesiastical", "vestry",
                              "tabernacle", "place of worship", "gospel hall",
                              "meeting house", "nave", "minster", "priory",
                              "abbey", "cathedral", "auditorium", "religious building"]):
        return "church"
    if any(k in t for k in ["village hall", "community hall", "masonic",
                              "memorial hall", "drill hall", "parish hall",
                              "church hall", "assembly hall", "civic hall",
                              "place of gathering"]):
        return "hall"
    if any(k in t for k in ["warehouse", "mill", "theatre", "cinema",
                              "bingo hall", "former school", "barn"]):
        return "large_space"
    return "other"


def extract_price(text: str) -> str:
    m = re.search(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?', text)
    return m.group(0) if m else ""


async def scrape_images_from_page(client, url: str, selectors: list = None) -> list[str]:
    try:
        r = await client.get(url, timeout=15, follow_redirects=True)
        if r.status_code != 200:
            return []
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "lxml")
        images = []
        default_selectors = selectors or [
            "div[class*=gallery] img", "div[class*=slider] img",
            "div[class*=carousel] img", "div[class*=photo] img",
            "figure img", "div[class*=property] img",
        ]
        for sel in default_selectors:
            for img in soup.select(sel):
                src = (img.get("src") or img.get("data-src") or
                       img.get("data-lazy-src") or img.get("data-original", ""))
                if src and src.startswith("http") and src not in images:
                    if not any(x in src for x in ["logo","icon","avatar","banner","placeholder"]):
                        images.append(src)
            if images:
                break
        if not images:
            for meta in soup.select("meta[property='og:image']"):
                content = meta.get("content", "")
                if content and content.startswith("http"):
                    images.append(content)
                    break
        return images[:5]
    except Exception as e:
        logger.debug("Image scrape failed for %s: %s", url, e)
        return []


class BaseScraper(ABC):
    source_name: str = ""
    source_type: str = "httpx"

    def __init__(self):
        self.logger = logging.getLogger(f"scrapers.{self.__class__.__name__}")

    @abstractmethod
    async def scrape(self, client) -> list[ScrapedListing]:
        ...

    def make_listing(self, **kwargs) -> ScrapedListing:
        return ScrapedListing(source=self.source_name, **kwargs)

    def log_result(self, count: int) -> None:
        self.logger.info("%s: %d listings found", self.source_name, count)
