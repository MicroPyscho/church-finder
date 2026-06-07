import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import httpx

from app.database import get_db
from app.models import Listing, CrawlRun

router = APIRouter()
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}


@router.get("")
async def get_listings(page: int = 1, per_page: int = 20, db: AsyncSession = Depends(get_db)):
    q     = select(Listing).where(Listing.is_active == True).order_by(Listing.first_seen.desc())
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(q.offset((page-1)*per_page).limit(per_page))).scalars().all()
    return {"total": total, "page": page, "per_page": per_page, "results": [_to_dict(r) for r in rows]}


@router.get("/runs")
async def get_crawl_runs(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(20))).scalars().all()
    return [{"id": r.id, "started_at": r.started_at.isoformat(),
             "finished_at": r.finished_at.isoformat() if r.finished_at else None,
             "new_listings": r.new_listings, "total_scraped": r.total_scraped,
             "triggered_by": r.triggered_by, "errors": r.errors} for r in rows]


@router.post("/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks, source: str = "all"):
    background_tasks.add_task(_run_crawl, source)
    return {"status": "started", "source": source}


async def _run_crawl(source: str = "all"):
    from app.database import AsyncSessionLocal
    from app.scrapers.registry import SCRAPERS

    run_start = datetime.utcnow()
    all_listings = []
    errors = []

    scrapers_to_run = {k: v for k, v in SCRAPERS.items() if k == source} if source != "all" else SCRAPERS

    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        for name, scraper_class in scrapers_to_run.items():
            try:
                logger.info("Scraping: %s", name)
                listings = await scraper_class().scrape(client)
                logger.info("%s: %d found", name, len(listings))
                all_listings.extend(listings)
            except Exception as e:
                msg = f"{name}: {e}"; logger.error(msg); errors.append(msg)

    # Deduplicate
    seen = {}
    for l in all_listings:
        if l.is_valid() and l.id not in seen:
            seen[l.id] = l
    deduped = list(seen.values())

    async with AsyncSessionLocal() as db:
        run = CrawlRun(started_at=run_start, finished_at=datetime.utcnow(),
                       triggered_by="api", new_listings=0, total_scraped=len(all_listings),
                       errors="\n".join(errors[:20]))
        db.add(run); await db.flush()

        new_count = 0
        for l in deduped:
            try:
                existing = await db.get(Listing, l.id)
                images_str = json.dumps(l.images_json) if l.images_json else None
                if existing:
                    existing.last_seen = datetime.utcnow()
                    existing.is_active = True
                    if l.price_raw not in ("","POA","Enquire","Guide TBC"):
                        existing.price = l.price_raw
                    if images_str and not existing.images:
                        existing.images = images_str
                else:
                    db.add(Listing(
                        id=l.id, source=l.source, title=l.title,
                        price=l.price_raw, location=l.location,
                        url=l.url, description=l.description,
                        images=images_str,
                    ))
                    new_count += 1
            except Exception as e:
                errors.append(f"DB {l.id}: {e}")

        run.new_listings = new_count
        run.errors = "\n".join(errors[:20])
        await db.commit()
    logger.info("Crawl done: %d new / %d total", new_count, len(all_listings))


def _to_dict(l: Listing) -> dict:
    images = []
    try:
        images = json.loads(l.images) if l.images else []
    except: pass
    return {
        "id": l.id, "source": l.source, "title": l.title,
        "price": l.price, "location": l.location, "url": l.url,
        "description": l.description, "images": images,
        "image_url": images[0] if images else None,
        "first_seen": l.first_seen.isoformat(),
        "last_seen": l.last_seen.isoformat(), "is_active": l.is_active,
    }
