import asyncio, hashlib, logging, re
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Listing, CrawlRun

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CORE_KEYWORDS = [
    "church","chapel","ecclesiastical","vestry","nave","place of worship",
    "religious building","tabernacle","congregation","parish","minster",
    "priory","abbey","meeting house","mission hall","redundant church",
    "former church","methodist","baptist","anglican","quaker",
    "salvation army","kingdom hall","united reformed","gospel hall",
    "village hall","community hall","assembly hall","masonic hall",
    "memorial hall","working men","drill hall","civic hall","parish hall",
    "banqueting hall","institute building","former theatre","former cinema",
    "bingo hall","former school","leisure centre","change of use",
    "listed building","surplus property","disposal","graveyard","churchyard",
    "high ceiling","clear span","auditorium","warehouse conversion",
    "mill building","barn conversion","diocese",
]

RIGHTMOVE_REGIONS = [
    ("Kent","REGION%5E61"),("East Sussex","REGION%5E45"),
    ("West Sussex","REGION%5E46"),("Surrey","REGION%5E91"),
    ("Hampshire","REGION%5E54"),("Oxfordshire","REGION%5E74"),
    ("Essex","REGION%5E47"),("Suffolk","REGION%5E90"),
    ("Yorkshire","REGION%5E103"),("Lancashire","REGION%5E62"),
    ("Gloucestershire","REGION%5E50"),("Somerset","REGION%5E85"),
    ("Devon","REGION%5E36"),("Norfolk","REGION%5E70"),
    ("Wiltshire","REGION%5E101"),("Berkshire","REGION%5E7"),
    ("Hertfordshire","REGION%5E55"),("Cambridgeshire","REGION%5E16"),
    ("Dorset","REGION%5E38"),("Lincolnshire","REGION%5E64"),
]

OTM_REGIONS = [
    "kent","east-sussex","surrey","hampshire","oxfordshire",
    "essex","suffolk","yorkshire","lancashire","gloucestershire",
    "somerset","devon","norfolk","wiltshire","berkshire",
]

def make_id(s, u): return hashlib.md5(f"{s}:{u}".encode()).hexdigest()
def has_kw(t): tl = t.lower(); return any(k in tl for k in CORE_KEYWORDS)
def price_from_text(t):
    m = re.search(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?', t)
    return m.group(0) if m else ""
def classify(t):
    tl = t.lower()
    if any(k in tl for k in ["church","chapel","ecclesiastical","vestry","tabernacle","place of worship","gospel hall","meeting house","nave","minster","priory","abbey"]): return "church"
    if any(k in tl for k in ["village hall","community hall","masonic","memorial hall","drill hall","parish hall","working men","civic hall","assembly hall"]): return "hall"
    if any(k in tl for k in ["warehouse","mill","theatre","cinema","bingo hall","former school","leisure centre","barn","industrial"]): return "large_space"
    return "other"

async def fetch(client, url):
    try:
        r = await client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as exc:
        logger.warning("Fetch failed %s: %s", url, exc)
        return None

# ── PROPERTY PORTALS ──────────────────────────────────────────────────────────

async def scrape_rightmove(client):
    results = []; seen = set()
    for label, rid in RIGHTMOVE_REGIONS:
        for term in ["church", "chapel"]:
            url = f"https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier={rid}&keywords={term}&sortType=6&includeSSTC=false"
            soup = await fetch(client, url)
            if not soup: continue

            # Try multiple selectors — Rightmove changes their HTML periodically
            cards = (
                soup.select("div.l-searchResult") or
                soup.select("div[class*=propertyCard]") or
                soup.select("article[class*=property]") or
                soup.select("div[data-test*=iterable]")
            )

            for card in cards:
                # Try multiple link selectors
                link = (
                    card.select_one("a.propertyCard-link") or
                    card.select_one("a[href*='/properties/']") or
                    card.select_one("a[href*='rightmove']")
                )
                if not link: continue
                href = link.get("href", "")
                if not href.startswith("http"): href = "https://www.rightmove.co.uk" + href
                if href in seen: continue
                seen.add(href)

                text = card.get_text(" ", strip=True)
                if not has_kw(text): continue

                title_el = (
                    card.select_one("h2.propertyCard-title") or
                    card.select_one("h2") or
                    card.select_one("[class*=title]")
                )
                price_el = (
                    card.select_one("div.propertyCard-priceValue") or
                    card.select_one("[class*=price]")
                )
                addr_el = (
                    card.select_one("address.propertyCard-address") or
                    card.select_one("address") or
                    card.select_one("[class*=address]")
                )
                desc_el = card.select_one("div.propertyCard-description") or card.select_one("[class*=description]")

                title = title_el.get_text(strip=True) if title_el else text[:120]
                desc  = desc_el.get_text(strip=True) if desc_el else ""

                results.append({
                    "id":            make_id("rightmove", href),
                    "source":        "Rightmove",
                    "title":         title[:300],
                    "price":         price_el.get_text(strip=True) if price_el else "POA",
                    "location":      addr_el.get_text(strip=True) if addr_el else label,
                    "url":           href,
                    "description":   desc[:400],
                    "property_type": classify(f"{title} {desc}"),
                })
            await asyncio.sleep(2)
    return results


async def scrape_onthemarket(client):
    results = []; seen = set()
    for region in OTM_REGIONS:
        url = f"https://www.onthemarket.com/for-sale/property/{region}/?keywords=church"
        soup = await fetch(client, url)
        if not soup: continue

        cards = (
            soup.select("li.otm-PropertyCardInfo") or
            soup.select("div[class*=property-card]") or
            soup.select("article") or
            soup.select("li[class*=property]")
        )

        for card in cards:
            link = card.select_one("a[href]")
            if not link: continue
            href = link.get("href", "")
            if not href.startswith("http"): href = "https://www.onthemarket.com" + href
            if href in seen: continue
            seen.add(href)
            text = card.get_text(" ", strip=True)
            if not has_kw(text): continue
            title_el = card.select_one("h2,h3,[class*=title]")
            price_el = card.select_one("[class*=price]")
            addr_el  = card.select_one("[class*=address],[class*=location]")
            results.append({
                "id":            make_id("otm", href),
                "source":        "OnTheMarket",
                "title":         title_el.get_text(strip=True) if title_el else text[:120],
                "price":         price_el.get_text(strip=True) if price_el else "POA",
                "location":      addr_el.get_text(strip=True) if addr_el else region,
                "url":           href,
                "description":   text[:400],
                "property_type": classify(text),
            })
        await asyncio.sleep(2)
    return results


async def scrape_clive_emson(client):
    results = []; seen = set()
    for term in ["church","chapel","hall","former+school","community+hall","place+of+worship"]:
        url = f"https://www.cliveemson.co.uk/properties/?keyword={term}"
        soup = await fetch(client, url)
        if not soup: continue
        for card in soup.select("div.lot"):
            title    = card.get("data-cathead", "").strip()
            price    = card.get("data-price", "").strip()
            location = card.get("data-loc", "").strip()
            lot_num  = card.get("data-lot", "")
            auction  = card.get("data-auc", "")
            if not title:
                t = card.select_one("h2,h3,.lot-title")
                title = t.get_text(strip=True) if t else ""
            if not has_kw(title): continue
            if not price:
                price = price_from_text(card.get_text(" ", strip=True)) or "Nil Reserve"
            if auction and lot_num:
                href = f"https://www.cliveemson.co.uk/properties/{auction}/lot-{lot_num}/"
            else:
                link = card.select_one("a[href]")
                href = link.get("href", "") if link else ""
                if href.startswith("/"): href = "https://www.cliveemson.co.uk" + href
            if not href or href in seen: continue
            seen.add(href)
            results.append({
                "id":            make_id("clive_emson", href),
                "source":        "Clive Emson Auctions",
                "title":         title,
                "price":         price,
                "location":      location or "South East",
                "url":           href,
                "description":   card.get_text(" ", strip=True)[:400],
                "property_type": classify(title),
            })
        await asyncio.sleep(2)
    return results


async def scrape_allsop(client):
    results = []
    for url in [
        "https://www.allsop.co.uk/auctions/residential-auctions/",
        "https://www.allsop.co.uk/auctions/commercial-auctions/",
    ]:
        soup = await fetch(client, url)
        if not soup: continue
        # Allsop loads lots dynamically — try to find any lot references
        for lot in soup.select("div.lot,article.lot,div[class*=lot],div[class*=property],li[class*=lot]"):
            text = lot.get_text(" ", strip=True)
            if not has_kw(text): continue
            link = lot.select_one("a[href]")
            if not link: continue
            href = link.get("href", url)
            if href.startswith("/"): href = "https://www.allsop.co.uk" + href
            title_el = lot.select_one("h2,h3,[class*=title]")
            price_el = lot.select_one("[class*=guide],[class*=price]")
            addr_el  = lot.select_one("[class*=address],[class*=location]")
            results.append({
                "id":            make_id("allsop", href),
                "source":        "Allsop Auctions",
                "title":         title_el.get_text(strip=True) if title_el else text[:120],
                "price":         price_el.get_text(strip=True) if price_el else price_from_text(text) or "TBC",
                "location":      addr_el.get_text(strip=True) if addr_el else "England",
                "url":           href,
                "description":   text[:400],
                "property_type": classify(text),
            })
        await asyncio.sleep(2)
    return results


# ── CHURCH BODIES ─────────────────────────────────────────────────────────────

# Words that indicate a nav link or resource page — NOT a property listing
COFE_EXCLUSIONS = [
    "resources", "administration", "committee", "reorganisation",
    "maintenance", "legacy", "regular", "llf", "resourcing",
    "pastoral measure", "mission and pastoral", "church growth",
    "faculty", "safeguarding", "governance", "training",
    "social media", "communications", "newsletter",
]

async def scrape_church_of_england(client):
    """
    Church of England property pages.
    Strict filtering to avoid scraping nav links and resource pages.
    Only include pages that look like actual property listings.
    """
    results = []
    property_urls = [
        "https://www.churchofengland.org/resources/property/churches-for-sale",
        "https://www.churchofengland.org/resources/property/commercial-property",
        "https://www.churchofengland.org/resources/property/residential-property",
    ]

    for url in property_urls:
        soup = await fetch(client, url)
        if not soup: continue

        for item in soup.select("div.property-listing,article,div.views-row,li.property,div.field-item"):
            text = item.get_text(" ", strip=True)

            # Must have enough content to be a real listing
            if len(text) < 30: continue

            # Must have a property-related keyword
            if not has_kw(text): continue

            # Must NOT be a nav/resource link
            text_lower = text.lower()
            if any(excl in text_lower for excl in COFE_EXCLUSIONS): continue

            link = item.select_one("a[href]")
            if not link: continue

            href = link.get("href", "")
            if href.startswith("/"): href = "https://www.churchofengland.org" + href

            # Skip links back to the same resource pages
            if any(excl.replace(" ","-") in href for excl in ["resources","committee","administration"]): continue

            title_el = item.select_one("h2,h3,.title,.property-title")
            title = title_el.get_text(strip=True) if title_el else text[:120]

            # Final check — title must sound like a property
            if not has_kw(title) and not any(w in title.lower() for w in ["sale","let","lease","available","property","land","building"]):
                continue

            results.append({
                "id":            make_id("cofe", href),
                "source":        "Church of England",
                "title":         title,
                "price":         "Enquire",
                "location":      "England",
                "url":           href,
                "description":   text[:400],
                "property_type": "church",
            })
        await asyncio.sleep(2)
    return results


async def scrape_methodist(client):
    results = []
    soup = await fetch(client, "https://www.methodist.org.uk/for-churches/property/property-for-sale/")
    if not soup: return results
    for item in soup.select("div.entry,article,div.property-item,li"):
        text = item.get_text(" ", strip=True)
        if len(text) < 30 or not has_kw(text): continue
        link = item.select_one("a[href]")
        if not link: continue
        href = link.get("href", "")
        if href.startswith("/"): href = "https://www.methodist.org.uk" + href
        results.append({
            "id":            make_id("methodist", href),
            "source":        "Methodist Church",
            "title":         text[:120],
            "price":         "Enquire",
            "location":      "England",
            "url":           href,
            "description":   text[:400],
            "property_type": "church",
        })
    return results


async def scrape_baptist(client):
    results = []
    soup = await fetch(client, "https://www.baptist.org.uk/Articles/368986/Properties_for_Sale.aspx")
    if not soup: return results
    for item in soup.select("div.property,article,li.property-item,div.entry,p"):
        text = item.get_text(" ", strip=True)
        if len(text) < 30 or not has_kw(text): continue
        link = item.select_one("a[href]")
        if not link: continue
        href = link.get("href", "")
        if not href.startswith("http"): href = "https://www.baptist.org.uk" + href
        results.append({
            "id":            make_id("baptist", href),
            "source":        "Baptist Union",
            "title":         text[:120],
            "price":         "Enquire",
            "location":      "England",
            "url":           href,
            "description":   text[:400],
            "property_type": "church",
        })
    return results


async def scrape_heritage_at_risk(client):
    results = []
    url = "https://historicengland.org.uk/advice/heritage-at-risk/search-register/?term=church&type=place-of-worship"
    soup = await fetch(client, url)
    if not soup: return results
    for item in soup.select("div.search-result,article.har-entry,li.result"):
        text = item.get_text(" ", strip=True)
        if len(text) < 20: continue
        link = item.select_one("a[href]")
        if not link: continue
        href = link.get("href", "")
        if href.startswith("/"): href = "https://historicengland.org.uk" + href
        title_el = item.select_one("h2,h3,.entry-title")
        addr_el  = item.select_one(".address,.location")
        results.append({
            "id":            make_id("heritage", href),
            "source":        "Heritage at Risk Register",
            "title":         title_el.get_text(strip=True) if title_el else text[:120],
            "price":         "Heritage at Risk",
            "location":      addr_el.get_text(strip=True) if addr_el else "England",
            "url":           href,
            "description":   f"[HERITAGE AT RISK] {text[:400]}",
            "property_type": "church",
        })
    return results


# ── DEDUPLICATION ─────────────────────────────────────────────────────────────

def deduplicate(listings):
    """
    Cross-source deduplication.
    Key: normalised title + first word of location.
    Keeps highest-confidence source when duplicate found.
    """
    CONFIDENCE = {
        "Church of England": 0.98, "Methodist Church": 0.96,
        "Baptist Union": 0.96, "Heritage at Risk Register": 0.99,
        "Rightmove": 0.95, "OnTheMarket": 0.92,
        "Clive Emson Auctions": 0.93, "Allsop Auctions": 0.93,
    }

    seen = {}
    for l in listings:
        # Normalise title for comparison
        title_norm = re.sub(r'[^a-z0-9]', '', l['title'].lower())[:25]
        loc_norm   = l['location'].lower().split()[0] if l.get('location') else ''
        key        = f"{title_norm}|{loc_norm}"

        if key not in seen:
            seen[key] = l
        else:
            existing_conf = CONFIDENCE.get(seen[key]["source"], 0.5)
            new_conf      = CONFIDENCE.get(l["source"], 0.5)
            if new_conf > existing_conf:
                seen[key] = l

    return list(seen.values())


# ── SCRAPER REGISTRY ──────────────────────────────────────────────────────────

ALL_SCRAPERS = [
    ("rightmove",          scrape_rightmove),
    ("onthemarket",        scrape_onthemarket),
    ("clive_emson",        scrape_clive_emson),
    ("allsop",             scrape_allsop),
    ("church_of_england",  scrape_church_of_england),
    ("methodist",          scrape_methodist),
    ("baptist",            scrape_baptist),
    ("heritage_at_risk",   scrape_heritage_at_risk),
]


# ── MAIN CRAWL ────────────────────────────────────────────────────────────────

async def run_crawl(db: AsyncSession, triggered_by: str = "scheduler", source: str = "all") -> CrawlRun:
    run = CrawlRun(started_at=datetime.utcnow(), triggered_by=triggered_by)
    db.add(run); await db.flush()

    errors = []; total = 0; new_count = 0; all_listings = []
    scrapers = ALL_SCRAPERS if source == "all" else [(n, f) for n, f in ALL_SCRAPERS if n == source]

    async with httpx.AsyncClient() as client:
        for name, fn in scrapers:
            try:
                logger.info("Scraping: %s", name)
                found = await fn(client)
                logger.info("%s: %d found", name, len(found))
                all_listings.extend(found); total += len(found)
            except Exception as exc:
                msg = f"{name}: {exc}"; logger.error(msg); errors.append(msg)

    deduped = deduplicate(all_listings)
    logger.info("After dedup: %d unique from %d total", len(deduped), total)

    for data in deduped:
        try:
            existing = await db.get(Listing, data["id"])
            if existing:
                existing.last_seen = datetime.utcnow()
                existing.is_active = True
                if existing.price != data.get("price", "") and data.get("price") not in ("Guide TBC", "", "POA"):
                    existing.price = data["price"]
            else:
                db.add(Listing(
                    id          = data["id"],
                    source      = data["source"],
                    title       = data["title"],
                    price       = data["price"],
                    location    = data["location"],
                    url         = data["url"],
                    description = data.get("description", ""),
                ))
                new_count += 1
        except Exception as exc:
            errors.append(f"DB {data.get('id','?')}: {exc}")

    run.finished_at   = datetime.utcnow()
    run.new_listings  = new_count
    run.total_scraped = total
    run.errors        = "\n".join(errors[:20])

    await db.commit()
    logger.info("Crawl done: %d new / %d total", new_count, total)
    return run
