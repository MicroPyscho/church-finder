import math
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Listing, CrawlRun
from app.schemas import ListingOut, ListingsPage, CrawlRunOut, CrawlTriggerResponse
from app.crawler import run_crawl

router = APIRouter()


@router.get("", response_model=ListingsPage)
async def get_listings(
    page:     int   = Query(1,  ge=1),
    per_page: int   = Query(20, ge=1, le=100),
    source:   str   = Query("", description="Filter by source name"),
    search:   str   = Query("", description="Search title/location"),
    db:       AsyncSession = Depends(get_db),
):
    q = select(Listing).where(Listing.is_active == True)

    if source:
        q = q.where(Listing.source.ilike(f"%{source}%"))
    if search:
        term = f"%{search}%"
        q = q.where(
            Listing.title.ilike(term) | Listing.location.ilike(term)
        )

    total_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(total_q)).scalar_one()

    q = q.order_by(Listing.first_seen.desc())
    q = q.offset((page - 1) * per_page).limit(per_page)

    rows = (await db.execute(q)).scalars().all()

    return ListingsPage(
        items=rows,
        total=total,
        page=page,
        pages=math.ceil(total / per_page) if total else 1,
    )


@router.get("/runs", response_model=list[CrawlRunOut])
async def get_crawl_runs(
    limit: int = Query(20, ge=1, le=100),
    db:    AsyncSession = Depends(get_db),
):
    q    = select(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.post("/crawl", response_model=CrawlTriggerResponse)
async def trigger_crawl(
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    run = CrawlRun(triggered_by="manual")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(run_crawl, db, "manual")

    return CrawlTriggerResponse(
        run_id=run.id,
        message="Crawl started in background",
    )
    
    