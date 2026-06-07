import asyncio, hashlib, logging, re, json
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Listing, CrawlRun

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}

# These must appear in the TITLE or DESCRIPTION — not just anywhere in the page
# This prevents matching "Church Street", "Church Road", "Charles Church" etc.
TITLE_KEYWORDS = [
    "church", "chapel", "ecclesiastical", "vestry", "nave",
    "place of worship", "tabernacle", "minster", "priory", "abbey",
    "meeting house", "mission hall", "former church", "redundant church",
    "methodist", "baptist", "gospel hall", "kingdom hall",
    "village hall", "community hall", "assembly hall", "masonic hall",
    "memorial hall", "drill hall", "civic hall", "parish hall",
    "former theatre", "former cinema", "bingo hall", "former school",
    "graveyard", "churchyard", "vestry", "presbytery",
]

# These are exclusions — if the title ONLY matches because of these, skip it
FALSE_POSITIVE_PATTERNS = [
    r"^church (road|street|lane|avenue|close|drive|way|place|court|terrace|end|hill|view|farm)",
    r"church (road|street|lane|avenue|close|drive|way|place|court|terrace|end|hill|view|farm)$",
    r"charles church",   # new build developer
    r"church & hawes",   # estate agent
    r"church lukas",     # estate agent
    r"\d+ church (road|street|lane)",  # "42 Church Street"
]
FALSE_POSITIVE_RE = [re.compile(p, re.IGNORECASE) for p in FALSE_POSITIVE_PATTERNS]

def is_church_property(title: str, description: str = "") -> bool:
    """
    Returns True only if this is genuinely a church/chapel/hall property.
    Filters out false positives from street names and estate agent names.
    """
    combined = (title + " " + description).lower()
    title_lower = title.lower()

    # Must have at least one core keyword in title or description
    if not any(kw in combined for kw in TITLE_KEYWORDS):
        return False

    # Check if the match is only a false positive pattern in the title
    for fp in FALSE_POSITIVE_RE:
        if fp.search(title_lower):
            # If ONLY a false positive matches, reject
            # But if another keyword also matches, keep it
            other_kws = [kw for kw in TITLE_KEYWORDS
                        if kw in combined and kw not in ["church"]]
            if not other_kws:
                return False

    return True

def make_id(s, u): return hashlib.md5(f"{s}:{u}".encode()).hexdigest()

def price_from_text(t):
    m = re.search(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?', t)
    return m.group(0) if m else ""

def classify(t):
    tl = t.lower()
    if any(k in tl for k in ["church","chapel","ecclesiastical","vestry","tabernacle",
                               "place of worship","gospel hall","meeting house","nave",
                               "minster","priory","abbey"]): return "church"
    if any(k in tl for k in ["village hall","community hall","masonic","memorial hall",
                               "drill hall","parish hall","working men","civic hall",
                               "assembly hall"]): return "hall"
    if any(k in tl for k in ["warehouse","mill","theatre","cinema","bingo hall",
                               "former school","leisure centre","barn"]): return "large_space"
    return "other"

async def fetch(client, url):
    try:
        r = await client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r
    except Exception as exc:
        logger.warning("Fetch failed %s: %s", url, exc)
        return None

async def fetch_soup(client, url):
    r = await fetch(client, url)
    if not r: return None
    return BeautifulSoup(r.text, "lxml")

# ── RIGHTMOVE — via __NEXT_DATA__ JSON ──────────────────────────────────────

# Correct search terms for church properties specifically
# Using commercial property search to get actual buildings, not houses on Church Street
RIGHTMOVE_CHURCH_URLS = [
    # Commercial property search — actual buildings
    "https://www.rightmove.co.uk/commercial-property-for-sale/find.html?searchType=SALE&keywords=church",
    "https://www.rightmove.co.uk/commercial-property-for-sale/find.html?searchType=SALE&keywords=chapel",
    "https://www.rightmove.co.uk/commercial-property-for-sale/find.html?searchType=SALE&keywords=place+of+worship",
    "https://www.rightmove.co.uk/commercial-property-for-sale/find.html?searchType=SALE&keywords=former+church",
    # Residential with strong church keywords
    "https://www.rightmove.co.uk/property-for-sale/find.html?keywords=converted+chapel",
    "https://www.rightmove.co.uk/property-for-sale/find.html?keywords=former+chapel",
    "https://www.rightmove.co.uk/property-for-sale/find.html?keywords=converted+church",
    "https://www.rightmove.co.uk/property-for-sale/find.html?keywords=church+conversion",
]

async def scrape_rightmove(client):
    results = []; seen = set()
    for url in RIGHTMOVE_CHURCH_URLS:
        r = await fetch(client, url)
        if not r: continue
        soup = BeautifulSoup(r.text, "lxml")
        # Extract from __NEXT_DATA__ JSON
        for s in soup.find_all("script"):
            src = s.string or ""
            if len(src) > 50000:
                try:
                    data = json.loads(src)
                    props = data["props"]["pageProps"]["searchResults"]["properties"]
                    logger.info("Rightmove %s: %d properties in JSON", url.split("?")[1][:30], len(props))
                    for p in props:
                        addr = p.get("displayAddress","").replace("\n"," ").strip()
                        summary = p.get("summary","")
                        prop_url = "https://www.rightmove.co.uk" + p.get("propertyUrl","")
                        if prop_url in seen: continue
                        # Strict check — must be a genuine church property
                        if not is_church_property(addr, summary): continue
                        seen.add(prop_url)
                        price_data = p.get("price",{})
                        price_raw = ""
                        if price_data.get("displayPrices"):
                            price_raw = price_data["displayPrices"][0].get("displayPrice","POA")
                        # Get image
                        images = p.get("propertyImages",{})
                        img_url = None
                        if isinstance(images, dict):
                            main = images.get("mainImageSrc") or images.get("mainMapImageSrc")
                            img_url = main
                        results.append({
                            "id":            make_id("rightmove", prop_url),
                            "source":        "Rightmove",
                            "title":         addr or summary[:120],
                            "price":         price_raw or "POA",
                            "location":      addr,
                            "url":           prop_url,
                            "description":   summary[:400],
                            "property_type": classify(addr + " " + summary),
                            "image_url":     img_url,
                        })
                except: pass
        await asyncio.sleep(2)
    logger.info("Rightmove total: %d genuine church properties", len(results))
    return results

# ── ONTHEMARKET ──────────────────────────────────────────────────────────────

# More specific OTM searches
OTM_SEARCHES = [
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=former+chapel",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=former+church",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=converted+chapel",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=place+of+worship",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=church+conversion",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=chapel+conversion",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=methodist+chapel",
    "https://www.onthemarket.com/for-sale/property/uk/?keywords=baptist+chapel",
]

async def scrape_onthemarket(client):
    results = []; seen = set()
    for url in OTM_SEARCHES:
        soup = await fetch_soup(client, url)
        if not soup: continue
        cards = (
            soup.select("li.otm-PropertyCardInfo") or
            soup.select("div[class*=property-card]") or
            soup.select("article")
        )
        logger.info("OTM %s: %d cards", url.split("=")[-1], len(cards))
        for card in cards:
            link = card.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
            if not href.startswith("http"): href = "https://www.onthemarket.com" + href
            if href in seen: continue
            seen.add(href)
            text = card.get_text(" ", strip=True)
            title_el = card.select_one("h2,h3,[class*=title]")
            title = title_el.get_text(strip=True) if title_el else text[:120]
            # Strict check
            if not is_church_property(title, text): continue
            price_el = card.select_one("[class*=price]")
            addr_el  = card.select_one("[class*=address],[class*=location]")
            location = addr_el.get_text(strip=True) if addr_el else ""
            results.append({
                "id":            make_id("otm", href),
                "source":        "OnTheMarket",
                "title":         title,
                "price":         price_el.get_text(strip=True) if price_el else price_from_text(text) or "POA",
                "location":      location,
                "url":           href,
                "description":   text[:400],
                "property_type": classify(title + " " + text),
            })
        await asyncio.sleep(2)
    return results

# ── CLIVE EMSON ──────────────────────────────────────────────────────────────

async def scrape_clive_emson(client):
    results = []; seen = set()
    for term in ["church","chapel","hall","former+school","community+hall","place+of+worship"]:
        url = f"https://www.cliveemson.co.uk/properties/?keyword={term}"
        soup = await fetch_soup(client, url)
        if not soup: continue
        for card in soup.select("div.lot"):
            title    = card.get("data-cathead","").strip()
            price    = card.get("data-price","").strip()
            location = card.get("data-loc","").strip()
            lot_num  = card.get("data-lot","")
            auction  = card.get("data-auc","")
            if not title:
                t = card.select_one("h2,h3,.lot-title")
                title = t.get_text(strip=True) if t else ""
            if not is_church_property(title): continue
            if not price:
                price = price_from_text(card.get_text(" ",strip=True)) or "Nil Reserve"
            href = f"https://www.cliveemson.co.uk/properties/{auction}/lot-{lot_num}/" if auction and lot_num else ""
            if not href:
                link = card.select_one("a[href]")
                href = link.get("href","") if link else ""
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
                "description":   card.get_text(" ",strip=True)[:400],
                "property_type": classify(title),
            })
        await asyncio.sleep(2)
    return results

# ── SDL AUCTIONS ─────────────────────────────────────────────────────────────

async def scrape_sdl(client):
    results = []
    for term in ["church","chapel","hall","place+of+worship"]:
        url = f"https://www.sdlauctions.co.uk/property-list/?search={term}"
        soup = await fetch_soup(client, url)
        if not soup: continue
        for card in soup.select("div.property-item,article.property,li.property,div.lot-item,div.property"):
            text = card.get_text(" ",strip=True)
            title_el = card.select_one("h2,h3,.property-title,.lot-title")
            title = title_el.get_text(strip=True) if title_el else text[:120]
            if not is_church_property(title, text): continue
            link = card.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
            if href.startswith("/"): href = "https://www.sdlauctions.co.uk" + href
            price_el = card.select_one(".guide-price,.price,.lot-price")
            addr_el  = card.select_one(".address,.location,.property-location")
            results.append({
                "id":            make_id("sdl", href),
                "source":        "SDL Auctions",
                "title":         title,
                "price":         price_el.get_text(strip=True) if price_el else price_from_text(text) or "TBC",
                "location":      addr_el.get_text(strip=True) if addr_el else "England",
                "url":           href,
                "description":   text[:400],
                "property_type": classify(title),
            })
        await asyncio.sleep(2)
    return results

# ── UK AUCTION LIST ──────────────────────────────────────────────────────────

async def scrape_uk_auction_list(client):
    results = []
    for url in [
        "https://ukauctionlist.com/?s=church",
        "https://ukauctionlist.com/?s=chapel",
        "https://ukauctionlist.com/?s=place+of+worship",
    ]:
        soup = await fetch_soup(client, url)
        if not soup: continue
        for item in soup.select("article,div.property,div.lot,li.property-item"):
            text = item.get_text(" ",strip=True)
            title_el = item.select_one("h2,h3,.entry-title,.property-title")
            title = title_el.get_text(strip=True) if title_el else text[:120]
            if not is_church_property(title, text): continue
            link = item.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
            if href.startswith("/"): href = "https://ukauctionlist.com" + href
            price_el = item.select_one(".price,.guide-price")
            addr_el  = item.select_one(".address,.location")
            results.append({
                "id":            make_id("uk_auction_list", href),
                "source":        "UK Auction List",
                "title":         title,
                "price":         price_el.get_text(strip=True) if price_el else price_from_text(text) or "TBC",
                "location":      addr_el.get_text(strip=True) if addr_el else "England",
                "url":           href,
                "description":   text[:400],
                "property_type": classify(title),
            })
        await asyncio.sleep(2)
    return results

# ── EIG AUCTIONS ─────────────────────────────────────────────────────────────

async def scrape_eig(client):
    results = []
    for term in ["church","chapel","place of worship"]:
        url = f"https://www.eigpropertyauctions.co.uk/search?q={term.replace(' ','+')}"
        soup = await fetch_soup(client, url)
        if not soup: continue
        for item in soup.select("div.property,article,li.property,div.lot"):
            text = item.get_text(" ",strip=True)
            title_el = item.select_one("h2,h3,.title")
            title = title_el.get_text(strip=True) if title_el else text[:120]
            if not is_church_property(title, text): continue
            link = item.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
            if not href.startswith("http"): href = "https://www.eigpropertyauctions.co.uk" + href
            price_el = item.select_one(".price,.guide-price,.guide")
            addr_el  = item.select_one(".address,.location")
            results.append({
                "id":            make_id("eig", href),
                "source":        "EIG Property Auctions",
                "title":         title,
                "price":         price_el.get_text(strip=True) if price_el else price_from_text(text) or "TBC",
                "location":      addr_el.get_text(strip=True) if addr_el else "England",
                "url":           href,
                "description":   text[:400],
                "property_type": classify(title),
            })
        await asyncio.sleep(2)
    return results

# ── CHURCH BODIES ─────────────────────────────────────────────────────────────

COFE_EXCLUSIONS = [
    "resources","administration","committee","reorganisation","maintenance",
    "legacy","resourcing","safeguarding","governance","training","social media",
    "communications","newsletter","article","news","commission","housing",
    "archbishop","response","pastoral measure","llf","coming home",
]

async def scrape_church_of_england(client):
    results = []
    urls = [
        "https://www.churchofengland.org/resources/property/churches-for-sale",
        "https://www.churchofengland.org/resources/property/commercial-property",
    ]
    for url in urls:
        soup = await fetch_soup(client, url)
        if not soup: continue
        for item in soup.select("div.property-listing,article,div.views-row,li.property,div.field-item,div[class*=listing]"):
            text = item.get_text(" ",strip=True)
            if len(text) < 30: continue
            text_lower = text.lower()
            # Must have property keyword
            if not any(kw in text_lower for kw in TITLE_KEYWORDS): continue
            # Must NOT be a nav/resource/article link
            if any(excl in text_lower for excl in COFE_EXCLUSIONS): continue
            # Must not be an article page
            if "article" in text_lower or "07/" in text or "12/" in text: continue
            link = item.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
            if href.startswith("/"): href = "https://www.churchofengland.org" + href
            # Skip if URL contains exclusion terms
            if any(excl.replace(" ","-") in href for excl in ["resources","committee","administration","commission","housing","archbishop","coming-home"]): continue
            title_el = item.select_one("h2,h3,.title,.property-title")
            title = title_el.get_text(strip=True) if title_el else text[:120]
            if not is_church_property(title, text): continue
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
    # Try updated URL
    for url in [
        "https://www.methodist.org.uk/for-churches/property/",
        "https://www.methodist.org.uk/about-us/property/",
        "https://www.methodist.org.uk/property/",
    ]:
        soup = await fetch_soup(client, url)
        if not soup: continue
        for item in soup.select("div.entry,article,div.property-item,li,div[class*=listing]"):
            text = item.get_text(" ",strip=True)
            if len(text) < 30 or not is_church_property("", text): continue
            link = item.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
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
        if results: break
        await asyncio.sleep(2)
    return results

async def scrape_baptist(client):
    results = []
    for url in [
        "https://www.baptist.org.uk/Groups/220597/Property.aspx",
        "https://www.baptist.org.uk/Articles/368986/Properties_for_Sale.aspx",
        "https://www.baptist.org.uk/property",
    ]:
        soup = await fetch_soup(client, url)
        if not soup: continue
        for item in soup.select("div.property,article,li.property-item,div.entry,p,div[class*=listing]"):
            text = item.get_text(" ",strip=True)
            if len(text) < 30 or not is_church_property("", text): continue
            link = item.select_one("a[href]")
            if not link: continue
            href = link.get("href","")
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
        if results: break
        await asyncio.sleep(2)
    return results

# ── DEDUPLICATION ─────────────────────────────────────────────────────────────

def deduplicate(listings):
    CONFIDENCE = {
        "Church of England":0.98,"Methodist Church":0.96,"Baptist Union":0.96,
        "Rightmove":0.95,"OnTheMarket":0.92,
        "Clive Emson Auctions":0.93,"SDL Auctions":0.91,
        "UK Auction List":0.89,"EIG Property Auctions":0.90,
    }
    seen = {}
    for l in listings:
        title_norm = re.sub(r'[^a-z0-9]','',l['title'].lower())[:25]
        loc_norm   = l.get('location','').lower().split()[0] if l.get('location') else ''
        key        = f"{title_norm}|{loc_norm}"
        if key not in seen or CONFIDENCE.get(l["source"],0.5) > CONFIDENCE.get(seen[key]["source"],0.5):
            seen[key] = l
    return list(seen.values())

# ── REGISTRY ──────────────────────────────────────────────────────────────────

ALL_SCRAPERS = [
    ("rightmove",         scrape_rightmove),
    ("onthemarket",       scrape_onthemarket),
    ("clive_emson",       scrape_clive_emson),
    ("sdl",               scrape_sdl),
    ("uk_auction_list",   scrape_uk_auction_list),
    ("eig",               scrape_eig),
    ("church_of_england", scrape_church_of_england),
    ("methodist",         scrape_methodist),
    ("baptist",           scrape_baptist),
]

# ── MAIN CRAWL ────────────────────────────────────────────────────────────────

async def run_crawl(db: AsyncSession, triggered_by: str = "scheduler", source: str = "all") -> CrawlRun:
    run = CrawlRun(started_at=datetime.utcnow(), triggered_by=triggered_by)
    db.add(run); await db.flush()
    errors = []; total = 0; new_count = 0; all_listings = []
    scrapers = ALL_SCRAPERS if source == "all" else [(n,f) for n,f in ALL_SCRAPERS if n == source]

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
    logger.info("After dedup: %d unique from %d", len(deduped), total)

    for data in deduped:
        try:
            existing = await db.get(Listing, data["id"])
            if existing:
                existing.last_seen = datetime.utcnow(); existing.is_active = True
                if existing.price != data.get("price","") and data.get("price") not in ("Guide TBC","","POA"):
                    existing.price = data["price"]
            else:
                db.add(Listing(
                    id=data["id"], source=data["source"], title=data["title"],
                    price=data["price"], location=data["location"],
                    url=data["url"], description=data.get("description",""),
                ))
                new_count += 1
        except Exception as exc:
            errors.append(f"DB {data.get('id','?')}: {exc}")

    run.finished_at = datetime.utcnow(); run.new_listings = new_count
    run.total_scraped = total; run.errors = "\n".join(errors[:20])
    await db.commit()
    logger.info("Done: %d new / %d total", new_count, total)
    return run
