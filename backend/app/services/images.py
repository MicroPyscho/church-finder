"""
Image service for Sanctuary.

Priority:
1. Images scraped from listing source page (already done in scrapers)
2. Bing image search by property name + postcode (free, no key)
3. OpenStreetMap static map by postcode (free, no key, always works)
4. Emoji placeholder (frontend)

Images stored in DB on first fetch — never re-fetched (cached forever
unless listing is updated with no images).
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
                data = r.json()
                result = data.get("result", {})
                lat = result.get("latitude")
                lng = result.get("longitude")
                if lat and lng:
                    return float(lat), float(lng)
    except Exception as e:
        logger.debug("Postcode lookup failed: %s", e)
    return None


def make_osm_map_url(lat: float, lng: float) -> str:
    """Free OpenStreetMap static image — no key, no limit."""
    return (
        f"https://staticmap.openstreetmap.de/staticmap.php"
        f"?center={lat},{lng}&zoom=17&size=600x400&maptype=mapnik"
        f"&markers={lat},{lng},red-pushpin"
    )


async def search_bing_images(query: str, count: int = 3) -> list[str]:
    """
    Search Bing Images for a query string.
    Free — no API key required. Uses the public search endpoint.
    Results are image URLs ready to store in DB.
    """
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.bing.com/images/search?q={encoded}&form=HDRSC2&first=1"
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return []

        soup = BeautifulSoup(r.text, "lxml")
        images = []

        # Bing embeds image data in murl attributes
        for a in soup.select("a.iusc"):
            m_attr = a.get("m", "")
            if not m_attr:
                continue
            try:
                data = json.loads(m_attr)
                img_url = data.get("murl", "")
                if img_url and img_url.startswith("http"):
                    # Filter out logos, icons, tiny images
                    if not any(x in img_url.lower() for x in ["logo","icon","avatar","placeholder","thumb"]):
                        images.append(img_url)
                        if len(images) >= count:
                            break
            except:
                continue

        logger.info("Bing images for '%s': %d found", query[:50], len(images))
        return images

    except Exception as e:
        logger.warning("Bing image search failed: %s", e)
        return []


async def get_images_for_listing(
    title: str,
    location: str,
    description: str = "",
    postcode: str = "",
) -> list[str]:
    """
    Get images for a listing that has none.
    
    Strategy:
    1. Try Bing image search with property name + location
    2. Fall back to OSM static map if postcode available
    3. Return empty list if nothing found (emoji used in frontend)
    
    Called ONCE per listing — result stored in DB forever.
    """
    images = []

    # Step 1: Bing image search
    # Build a specific query: "Former Methodist Chapel Swanscombe Kent"
    search_query = f"{title} {location} church"
    # Clean up the query — remove auction jargon
    search_query = re.sub(
        r'\b(LOT \d+|GUIDE PRICE|NIL RESERVE|FREEHOLD|LEASEHOLD|FOR SALE|TO LET|AUCTION)\b',
        '', search_query, flags=re.IGNORECASE
    ).strip()
    search_query = re.sub(r'\s+', ' ', search_query).strip()

    if search_query:
        images = await search_bing_images(search_query, count=3)

    # Step 2: OSM map fallback
    if not images:
        # Try to find postcode in description or location
        pc = postcode
        if not pc:
            pc = await extract_postcode(description or "")
        if not pc:
            pc = await extract_postcode(location or "")

        if pc:
            latlon = await postcode_to_latlon(pc)
            if latlon:
                lat, lng = latlon
                map_url = make_osm_map_url(lat, lng)
                images = [map_url]
                logger.info("Using OSM map for %s (postcode: %s)", title[:40], pc)

    return images


async def enrich_all_without_images(db, limit: int = 50) -> int:
    """
    Background job — run after each crawl.
    Finds listings with no images and fetches them.
    Each listing is only processed ONCE (cached in DB after first fetch).
    """
    from sqlalchemy import text

    rows = (await db.execute(text(
        "SELECT id, title, location, description "
        "FROM listings "
        "WHERE is_active = true "
        "AND (images IS NULL OR images = '[]' OR images = '') "
        "LIMIT :limit"
    ), {"limit": limit})).all()

    if not rows:
        logger.info("No listings need image enrichment")
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
                logger.info("Images added for: %s", row.title[:40])
        except Exception as e:
            logger.warning("Image enrichment failed for %s: %s", row.id, e)

        # Polite delay — avoid hammering Bing
        await asyncio.sleep(1)

    if enriched:
        await db.commit()

    logger.info("Image enrichment complete: %d/%d listings enriched", enriched, len(rows))
    return enriched
