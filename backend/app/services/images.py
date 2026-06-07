"""
Image service for Sanctuary.
Writes to Mac first — never directly to container.
"""
import asyncio
import json
import logging
import re
import urllib.parse
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}

WATERMARKED = [
    "alamy.com", "gettyimages", "shutterstock", "istockphoto",
    "istock.com", "123rf.com", "dreamstime", "depositphotos",
    "adobestock", "stock.adobe", "bigstockphoto",
]

PREFERRED = [
    "visitchurches.org.uk", "geograph.org", "britishlistedbuildings",
    "historicengland.org.uk", "britainexpress.com", "seearoundbritain",
    "londonchurchbuildings", "churches-uk-ireland.org",
    "wikimedia.org", "wikipedia.org",
]


def is_watermarked(url: str) -> bool:
    return any(d in url.lower() for d in WATERMARKED)


def is_preferred(url: str) -> bool:
    return any(d in url.lower() for d in PREFERRED)


async def extract_postcode(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r'\b([A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2})\b', text.upper())
    return m.group(1).strip() if m else None


async def postcode_to_latlon(postcode: str) -> tuple[float, float] | None:
    try:
        clean = postcode.replace(" ", "").upper()
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"https://api.postcodes.io/postcodes/{clean}")
            if r.status_code == 200:
                data = r.json().get("result", {})
                lat, lng = data.get("latitude"), data.get("longitude")
                if lat and lng:
                    return float(lat), float(lng)
    except Exception as e:
        logger.debug("Postcode lookup failed: %s", e)
    return None


def osm_map_url(lat: float, lng: float) -> str:
    return (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lng}&zoom=17&size=600x400&maptype=mapnik"
        f"&markers={lat},{lng},red-pushpin"
    )


def clean_for_search(title: str) -> str:
    junk = [
        r'\bLOT\s+\d+\b', r'\bGUIDE\s+PRICE\b', r'\bNIL\s+RESERVE\b',
        r'\bFREEHOLD\b', r'\bLEASEHOLD\b', r'£[\d,]+(\s*[-–]\s*£[\d,]+)?',
        r'\bPOTENTIAL\b', r'\bFOUR\s+FLOORS?\b', r'\bTHREE\s+FLOORS?\b',
        r'\b(WITH|AND|THE|A|AN)\b', r'\bOVER\b', r'\bTOWN\s+CENTRE\b',
    ]
    result = title
    for p in junk:
        result = re.sub(p, ' ', result, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', result).strip()


async def search_bing_images(query: str, max_count: int = 3) -> list[str]:
    try:
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2"
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return []
        soup = BeautifulSoup(r.text, "lxml")
        preferred, others = [], []
        for a in soup.select("a.iusc"):
            try:
                data = json.loads(a.get("m", "{}"))
                img = data.get("murl", "")
                if not img or not img.startswith("http"):
                    continue
                if is_watermarked(img):
                    continue
                if any(x in img.lower() for x in ["logo","icon","avatar","banner","placeholder"]):
                    continue
                (preferred if is_preferred(img) else others).append(img)
            except:
                continue
        results = (preferred + others)[:max_count]
        logger.info("Bing '%s': %d images", query[:40], len(results))
        return results
    except Exception as e:
        logger.warning("Bing search failed: %s", e)
        return []


async def get_images_for_listing(title: str, location: str, description: str = "") -> list[str]:
    pc = await extract_postcode(description or "")
    if not pc:
        pc = await extract_postcode(location or "")

    clean = clean_for_search(title)
    query = f"{clean} {pc or location}".strip()

    images = []
    if query and len(query) > 5:
        images = await search_bing_images(query, max_count=3)

    if not images and pc:
        latlon = await postcode_to_latlon(pc)
        if latlon:
            images = [osm_map_url(*latlon)]

    return images


async def enrich_all_without_images(db, limit: int = 50) -> int:
    from sqlalchemy import text

    rows = (await db.execute(text(
        "SELECT id, title, location, description FROM listings "
        "WHERE is_active = true "
        "AND (images IS NULL OR images = '[]' OR images = '') "
        "LIMIT :limit"
    ), {"limit": limit})).all()

    if not rows:
        return 0

    enriched = 0
    for row in rows:
        try:
            images = await get_images_for_listing(
                title=row.title or "",
                location=row.location or "",
                description=row.description or "",
            )
            if images:
                await db.execute(text(
                    "UPDATE listings SET images = :imgs WHERE id = :id"
                ), {"imgs": json.dumps(images), "id": row.id})
                enriched += 1
        except Exception as e:
            logger.warning("Image enrichment failed %s: %s", row.id, e)
        await asyncio.sleep(1)

    if enriched:
        await db.commit()

    logger.info("Enriched %d/%d listings", enriched, len(rows))
    return enriched


async def replace_watermarked_images(db) -> int:
    """Find listings with Alamy/watermarked images and replace them."""
    from sqlalchemy import text

    rows = (await db.execute(text(
        "SELECT id, title, location, description, images FROM listings "
        "WHERE is_active = true AND images IS NOT NULL"
    ))).all()

    replaced = 0
    for row in rows:
        try:
            imgs = json.loads(row.images) if row.images else []
            if not any(is_watermarked(img) for img in imgs):
                continue
            # Replace watermarked images
            new_images = await get_images_for_listing(
                title=row.title or "",
                location=row.location or "",
                description=row.description or "",
            )
            if new_images:
                await db.execute(text(
                    "UPDATE listings SET images = :imgs WHERE id = :id"
                ), {"imgs": json.dumps(new_images), "id": row.id})
                replaced += 1
        except Exception as e:
            logger.warning("Replace watermarked failed %s: %s", row.id, e)
        await asyncio.sleep(1)

    if replaced:
        await db.commit()
    logger.info("Replaced watermarked images in %d listings", replaced)
    return replaced
