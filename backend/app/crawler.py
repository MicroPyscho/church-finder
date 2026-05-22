import asyncio
import hashlib
import logging
from datetime import datetime

import httpx
from scrapling import Fetcher
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Listing, CrawlRun

logger = logging.getLogger(__name__)

fetcher = Fetcher(auto_match=False)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


RIGHTMOVE_REGIONS = [
    ("Kent",            "REGION%5E61"),
    ("East Sussex",     "REGION%5E45"),
    ("West Sussex",     "REGION%5E46"),
    ("Surrey",          "REGION%5E91"),
    ("Hampshire",       "REGION%5E54"),
    ("Berkshire",       "REGION%5E7"),
    ("Oxfordshire",     "REGION%5E74"),
    ("Buckinghamshire", "REGION%5E13"),
    ("Hertfordshire",   "REGION%5E55"),
    ("Essex",           "REGION%5E46"),
    ("Suffolk",         "REGION%5E90"),
    ("Wiltshire",       "REGION%5E101"),
    ("Gloucestershire", "REGION%5E50"),
]

OTM_REGIONS = [
    "kent", "east-sussex", "west-sussex", "surrey", "hampshire",
    "berkshire", "oxfordshire", "buckinghamshire", "hertfordshire",
    "essex", "suffolk", "wiltshire",
]


def make_id(source: str, url: str) -> str:
    return hashlib.md5(f"{source}:{url}".encode()).hexdigest()


def has_keyword(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in settings.KEYWORDS)


async def fetch_html(client: httpx.AsyncClient, url: str):
    try:
        r = await client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        # Use Scrapling to parse — handles dynamic selectors better
        page = fetcher.fetch(url, headers=HEADERS)
        return page
    except Exception as exc:
        logger.warning("Fetch failed %s: %s", url, exc)
        return None

async def scrape_rightmove(client: httpx.AsyncClient) -> list[dict]:
    results = []
    for label, region_id in RIGHTMOVE_REGIONS:
        url = (
            f"https://www.rightmove.co.uk/property-for-sale/find.html"
            f"?locationIdentifier={region_id}&keywords=church&sortType=6"
        )
        soup = await fetch_html(client, url)
        if not soup:
            continue
        for card in soup.select("div.l-searchResult"):
            title_el = card.select_one("h2.propertyCard-title")
            price_el = card.select_one("div.propertyCard-priceValue")
            addr_el  = card.select_one("address.propertyCard-address")
            link_el  = card.select_one("a.propertyCard-link")
            desc_el  = card.select_one("div.propertyCard-description")
            if not link_el:
                continue
            href  = "https://www.rightmove.co.uk" + link_el.get("href", "")
            title = (title_el or desc_el or card).get_text(strip=True)[:300]
            desc  = desc_el.get_text(strip=True) if desc_el else ""
            if not has_keyword(f"{title} {desc}"):
                continue
            results.append({
                "id":          make_id("rightmove", href),
                "source":      f"Rightmove ({label})",
                "title":       title,
                "price":       price_el.get_text(strip=True) if price_el else "POA",
                "location":    addr_el.get_text(strip=True) if addr_el else label,
                "url":         href,
                "description": desc,
            })
        await asyncio.sleep(settings.REQUEST_DELAY_SECONDS)
    return results


async def scrape_onthemarket(client: httpx.AsyncClient) -> list[dict]:
    results = []
    for region in OTM_REGIONS:
        url = (
            f"https://www.onthemarket.com/for-sale/property/{region}/"
            f"?search-type=property&keywords=church&recently-added=24-hours"
        )
        soup = await fetch_html(client, url)
        if not soup:
            continue
        for card in soup.select("li.otm-PropertyCardInfo"):
            link_el  = card.select_one("a[href]")
            title_el = card.select_one("h2.title")
            price_el = card.select_one("p.price")
            addr_el  = card.select_one("p.address")
            if not link_el:
                continue
            href = "https://www.onthemarket.com" + link_el.get("href", "")
            text = card.get_text(" ", strip=True)
            if not has_keyword(text):
                continue
            results.append({
                "id":          make_id("otm", href),
                "source":      f"OnTheMarket ({region})",
                "title":       title_el.get_text(strip=True) if title_el else "Property",
                "price":       price_el.get_text(strip=True) if price_el else "POA",
                "location":    addr_el.get_text(strip=True) if addr_el else region,
                "url":         href,
                "description": "",
            })
        await asyncio.sleep(settings.REQUEST_DELAY_SECONDS)
    return results


async def scrape_clive_emson(client: httpx.AsyncClient) -> list[dict]:
    results = []
    url   = "https://www.cliveemson.co.uk/property-auctions/upcoming-auctions/"
    soup  = await fetch_html(client, url)
    if not soup:
        return results
    for lot in soup.select("article.lot, div.lot-item, div.property-item"):
        text = lot.get_text(" ", strip=True)
        if not has_keyword(text):
            continue
        link_el  = lot.select_one("a[href]")
        title_el = lot.select_one("h2, h3, .lot-title")
        price_el = lot.select_one(".guide-price, .price")
        addr_el  = lot.select_one(".address, .location")
        href = link_el.get("href", url) if link_el else url
        if href.startswith("/"):
            href = "https://www.cliveemson.co.uk" + href
        results.append({
            "id":          make_id("clive_emson", href),
            "source":      "Clive Emson Auctions",
            "title":       title_el.get_text(strip=True) if title_el else "Church Lot",
            "price":       price_el.get_text(strip=True) if price_el else "See guide",
            "location":    addr_el.get_text(strip=True) if addr_el else "South East",
            "url":         href,
            "description": text[:300],
        })
    return results


async def scrape_allsop(client: httpx.AsyncClient) -> list[dict]:
    results = []
    url  = "https://www.allsop.co.uk/residential-auctions/forthcoming-auction-lots/"
    soup = await fetch_html(client, url)
    if not soup:
        return results
    for lot in soup.select("div.lot, article.lot, div.property-result"):
        text = lot.get_text(" ", strip=True)
        if not has_keyword(text):
            continue
        link_el  = lot.select_one("a[href]")
        title_el = lot.select_one("h2, h3, .lot-title")
        price_el = lot.select_one(".guide, .guide-price")
        addr_el  = lot.select_one(".address, .location")
        href = link_el.get("href", url) if link_el else url
        if href.startswith("/"):
            href = "https://www.allsop.co.uk" + href
        results.append({
            "id":          make_id("allsop", href),
            "source":      "Allsop Auctions",
            "title":       title_el.get_text(strip=True) if title_el else "Church Lot",
            "price":       price_el.get_text(strip=True) if price_el else "TBC",
            "location":    addr_el.get_text(strip=True) if addr_el else "England",
            "url":         href,
            "description": text[:300],
        })
    return results


ALL_SCRAPERS = [
    scrape_rightmove,
    scrape_onthemarket,
    scrape_clive_emson,
    scrape_allsop,
]


async def run_crawl(db: AsyncSession, triggered_by: str = "scheduler") -> CrawlRun:
    run = CrawlRun(started_at=datetime.utcnow(), triggered_by=triggered_by)
    db.add(run)
    await db.flush()

    errors: list[str] = []
    total_scraped = 0
    new_count     = 0

    async with httpx.AsyncClient() as client:
        for scraper_fn in ALL_SCRAPERS:
            try:
                listings = await scraper_fn(client)
                total_scraped += len(listings)

                for data in listings:
                    existing = await db.get(Listing, data["id"])
                    if existing:
                        existing.last_seen = datetime.utcnow()
                        existing.is_active = True
                    else:
                        db.add(Listing(**data))
                        new_count += 1

            except Exception as exc:
                msg = f"{scraper_fn.__name__}: {exc}"
                logger.error(msg)
                errors.append(msg)

    run.finished_at   = datetime.utcnow()
    run.new_listings  = new_count
    run.total_scraped = total_scraped
    run.errors        = "\n".join(errors)

    await db.commit()
    logger.info("Crawl complete: %d new / %d total", new_count, total_scraped)
    return run

