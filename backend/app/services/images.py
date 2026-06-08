"""
Image service for Sanctuary.
Priority:
1. Images scraped from source listing page (scrapers handle this)
2. Bing image search: property name + full address/postcode (precise)
3. OSM static map using postcode (always works)

No watermarked images (Alamy, Getty, Shutterstock etc).
Cached in DB — called at most once per listing.
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
    "adobestock", "stock.adobe", "bigstockphoto", "fotolia",
]

PREFERRED = [
    "visitchurches.org.uk", "geograph.org", "britishlistedbuildings",
    "historicengland.org.uk", "britainexpress.com", "seearoundbritain",
    "londonchurchbuildings", "churches-uk-ireland.org",
    "wikimedia.org", "wikipedia.org", "churchesconservationtrust",
    "heritagegateway.org.uk", "coflein.gov.wales",
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


def build_image_query(title: str, location: str, description: str) -> str:
    """
    Build the most precise possible image search query.
    Priority: church name + postcode > church name + address > church name + location
    """
    # Clean auction jargon from title
    clean_title = re.sub(
        r'\b(LOT\s+\d+|GUIDE\s+PRICE|NIL\s+RESERVE|FREEHOLD|LEASEHOLD|'
        r'FOR\s+SALE|TO\s+LET|AUCTION|OFFERS?\s+(OVER|IN\s+EXCESS)|'
        r'POTENTIAL|FOUR\s+FLOORS?|THREE\s+FLOORS?|TOWN\s+CENTRE)\b',
        '', title, flags=re.IGNORECASE
    )
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()

    # Try to get postcode from location or description
    all_text = f"{location} {description}"
    pc_match = re.search(r'\b([A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2})\b', all_text.upper())
    postcode = pc_match.group(1) if pc_match else None

    # Try to extract street address from location
    # CoE location format: "Church Road, South Hylton" or "Landor Road, London, SW9 9JE"
    address_parts = [p.strip() for p in location.split(",") if p.strip()]

    if postcode:
        # Most precise: name + postcode
        return f"{clean_title} {postcode}".strip()
    elif len(address_parts) >= 2:
        # Name + first address line + town
        return f"{clean_title} {address_parts[0]} {address_parts[-1]}".strip()
    else:
        # Name + location
        return f"{clean_title} {location}".strip()


async def search_bing_images(query: str, max_count: int = 3) -> list[str]:
    """Search Bing Images. No watermarks. Prefer heritage sources."""
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
                if any(x in img.lower() for x in ["logo", "icon", "avatar", "banner", "placeholder"]):
                    continue
                (preferred if is_preferred(img) else others).append(img)
            except:
                continue

        results = (preferred + others)[:max_count]
        logger.info("Bing '%s': %d images (%d preferred)", query[:50], len(results), len(preferred))
        return results

    except Exception as e:
        logger.warning("Bing search failed: %s", e)
        return []


async def get_images_for_listing(
    title: str,
    location: str,
    description: str = "",
) -> list[str]:
    """
    Get images for a listing with no existing images.
    Uses precise query: name + postcode/address.
    Falls back to OSM map if no images found.
    """
    query = build_image_query(title, location, description)
    images = []

    if query and len(query) > 5:
        images = await search_bing_images(query, max_count=3)
        logger.info("Image query: '%s' → %d results", query[:60], len(images))

    # OSM map fallback
    if not images:
        pc = await extract_postcode(f"{location} {description}")
        if pc:
            latlon = await postcode_to_latlon(pc)
            if latlon:
                images = [osm_map_url(*latlon)]
                logger.info("OSM fallback for postcode %s", pc)

    return images


async def enrich_all_without_images(db, limit: int = 50) -> int:
    """
    Background job. Find listings with no images and fetch them.
    Each listing processed at most once — result cached in DB.
    """
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
    """Replace any listings that have watermarked images."""
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
