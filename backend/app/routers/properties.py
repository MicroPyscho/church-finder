import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Listing

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{property_id}")
async def get_property(property_id: str, db: AsyncSession = Depends(get_db)):
    listing = await db.get(Listing, property_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Property not found")
    images = []
    try:
        images = json.loads(listing.images) if listing.images else []
    except:
        pass
    def safe(attr, default=None):
        return getattr(listing, attr, default)
    return {
        "id":            listing.id,
        "source":        listing.source,
        "source_url":    listing.url,
        "title":         listing.title,
        "price_raw":     listing.price,
        "price":         listing.price,
        "location":      listing.location,
        "description":   listing.description,
        "images":        images,
        "image_url":     images[0] if images else None,
        "listing_type":  safe("listing_type", "sale"),
        "is_listed":     safe("is_listed", False),
        "listed_grade":  safe("listed_grade", ""),
        "is_off_market": safe("is_off_market", False),
        "county":        safe("county", ""),
        "postcode":      safe("postcode", ""),
        "has_parking":   safe("has_parking", False),
        "has_graveyard": safe("has_graveyard", False),
        "has_hall":      safe("has_hall", False),
        "has_spire":     safe("has_spire", False),
        "ai_score":      safe("ai_score"),
        "ai_summary":    safe("ai_summary", ""),
        "first_seen":    listing.first_seen.isoformat(),
        "last_seen":     listing.last_seen.isoformat(),
        "is_active":     listing.is_active,
        "_score":        100,
        "_criteria":     [],
    }
