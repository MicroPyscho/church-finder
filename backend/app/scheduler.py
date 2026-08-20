"""
Background scheduler for Sanctuary.

Jobs:
  - crawl_all_sources     every 3 hours — scrapes all httpx sources
  - enrich_images         every 6 hours — fills missing images
  - geocode_new_listings  every 1 hour  — geocodes new listings
"""
import asyncio
import logging
import json
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/London")


async def _crawl_all_sources():
    """Scrape all active httpx scrapers and save new listings to DB."""
    import httpx
    from app.scrapers.registry import SCRAPERS
    from app.database import AsyncSessionLocal
    from app.models import Listing

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    }

    all_listings = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=20,
                                  follow_redirects=True) as client:
        for name, cls in SCRAPERS.items():
            if getattr(cls, "source_type", "httpx") != "httpx":
                continue
            try:
                found = await cls().scrape(client)
                all_listings.extend(found)
                logger.info("Crawl %s: %d listings", name, len(found))
            except Exception as e:
                logger.warning("Crawl %s failed: %s", name, e)

    async with AsyncSessionLocal() as db:
        new = 0
        for l in all_listings:
            if not l.is_valid():
                continue
            existing = await db.get(Listing, l.id)
            if not existing:
                db.add(Listing(
                    id=l.id, source=l.source, title=l.title,
                    price=l.price_raw, location=l.location,
                    url=l.url, description=l.description,
                    images=json.dumps(l.images_json) if l.images_json else None,
                ))
                new += 1
        await db.commit()
        logger.info("Crawl complete — new: %d total scraped: %d", new, len(all_listings))


async def _enrich_images():
    """Fill missing images for listings that have none."""
    from app.database import AsyncSessionLocal
    from app.services.images import enrich_all_without_images
    async with AsyncSessionLocal() as db:
        count = await enrich_all_without_images(db, limit=30)
        if count:
            logger.info("Image enrichment: %d listings updated", count)


async def _geocode_new():
    """Geocode any listings that don't have lat/lon yet."""
    from app.database import AsyncSessionLocal
    from app.services.geocoder import geocode_all_listings
    async with AsyncSessionLocal() as db:
        count = await geocode_all_listings(db)
        if count:
            logger.info("Geocoding: %d listings geocoded", count)


def start_scheduler(crawl_hours: int = 3):
    """Start all background jobs."""
    scheduler.add_job(
        _crawl_all_sources,
        trigger=IntervalTrigger(hours=crawl_hours),
        id="crawl_all_sources",
        name="Scrape all listing sources",
        replace_existing=True,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        _enrich_images,
        trigger=IntervalTrigger(hours=6),
        id="enrich_images",
        name="Fill missing property images",
        replace_existing=True,
    )
    scheduler.add_job(
        _geocode_new,
        trigger=IntervalTrigger(hours=1),
        id="geocode_new",
        name="Geocode new listings",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — crawl every %dh, images every 6h, geocode every 1h",
        crawl_hours
    )


def stop_scheduler():
    """Gracefully stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
