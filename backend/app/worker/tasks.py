import asyncio
import logging
import httpx
from datetime import datetime
from app.worker.celery import celery_app
from app.scrapers.registry import SCRAPERS
from app.scrapers.base import ScrapedListing, is_genuine_church

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}


@celery_app.task(name="app.worker.tasks.crawl_all")
def crawl_all():
    """Run all httpx scrapers. Playwright scrapers run separately."""
    asyncio.run(_crawl_all_async())


@celery_app.task(name="app.worker.tasks.crawl_source")
def crawl_source(source_name: str):
    """Run a single scraper by name."""
    asyncio.run(_crawl_source_async(source_name))


@celery_app.task(name="app.worker.tasks.match_alerts")
def match_alerts():
    """Match new listings against saved user alerts."""
    asyncio.run(_match_alerts_async())


async def _crawl_all_async():
    from app.database import AsyncSessionLocal
    from app.models import Listing, CrawlRun

    run_start = datetime.utcnow()
    all_listings = []
    errors = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        for name, scraper_class in SCRAPERS.items():
            try:
                scraper = scraper_class()
                listings = await scraper.scrape(client)
                all_listings.extend(listings)
                logger.info("%s: %d listings", name, len(listings))
            except Exception as e:
                msg = f"{name}: {e}"
                logger.error(msg)
                errors.append(msg)

    # Deduplicate
    seen = {}
    for l in all_listings:
        if not l.is_valid(): continue
        if l.id not in seen:
            seen[l.id] = l

    deduped = list(seen.values())
    logger.info("Deduped: %d unique from %d total", len(deduped), len(all_listings))

    # Save to database
    async with AsyncSessionLocal() as db:
        run = CrawlRun(
            started_at=run_start,
            finished_at=datetime.utcnow(),
            triggered_by="celery_scheduler",
            new_listings=0,
            total_scraped=len(all_listings),
            errors="\n".join(errors[:20]),
        )
        db.add(run)
        await db.flush()

        new_count = 0
        for listing in deduped:
            try:
                existing = await db.get(Listing, listing.id)
                if existing:
                    existing.last_seen = datetime.utcnow()
                    existing.is_active = True
                    if listing.price_raw and listing.price_raw not in ("Guide TBC","","POA","Enquire"):
                        existing.price = listing.price_raw
                else:
                    db.add(Listing(
                        id=listing.id,
                        source=listing.source,
                        title=listing.title,
                        price=listing.price_raw,
                        location=listing.location,
                        url=listing.url,
                        description=listing.description,
                    ))
                    new_count += 1
            except Exception as e:
                errors.append(f"DB {listing.id}: {e}")

        run.new_listings = new_count
        run.errors = "\n".join(errors[:20])
        await db.commit()

    logger.info("Crawl complete: %d new / %d total", new_count, len(all_listings))


async def _crawl_source_async(source_name: str):
    if source_name not in SCRAPERS:
        logger.error("Unknown source: %s", source_name)
        return
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        scraper = SCRAPERS[source_name]()
        listings = await scraper.scrape(client)
        logger.info("%s: %d listings found", source_name, len(listings))
        # Save...
        from app.database import AsyncSessionLocal
        from app.models import Listing
        async with AsyncSessionLocal() as db:
            for l in listings:
                if not l.is_valid(): continue
                existing = await db.get(Listing, l.id)
                if not existing:
                    db.add(Listing(
                        id=l.id, source=l.source, title=l.title,
                        price=l.price_raw, location=l.location,
                        url=l.url, description=l.description,
                    ))
            await db.commit()


async def _match_alerts_async():
    """Match new listings against user alerts and send notifications."""
    # TODO: implement alert matching
    logger.info("Alert matching: not yet implemented")
