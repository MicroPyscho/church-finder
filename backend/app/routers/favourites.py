import json
import logging
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Listing

router = APIRouter()
logger = logging.getLogger(__name__)

_favourites: dict[str, list[str]] = {}

def get_session(authorization: Optional[str] = Header(None)) -> str:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return "anonymous"

@router.get("")
async def list_favourites(session: str = Depends(get_session), db: AsyncSession = Depends(get_db)):
    ids = _favourites.get(session, [])
    if not ids:
        return []
    rows = (await db.execute(select(Listing).where(Listing.id.in_(ids), Listing.is_active == True))).scalars().all()
    result = []
    for l in rows:
        images = []
        try:
            images = json.loads(l.images) if l.images else []
        except:
            pass
        result.append({
            "id": l.id, "property_id": l.id,
            "property": {
                "id": l.id, "title": l.title, "price_raw": l.price,
                "location": l.location, "source": l.source,
                "source_url": l.url, "images": images,
                "image_url": images[0] if images else None,
                "is_off_market": getattr(l, "is_off_market", False),
                "first_seen": l.first_seen.isoformat(),
            }
        })
    return result

@router.post("/{property_id}")
async def add_favourite(property_id: str, session: str = Depends(get_session), db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    listing = await db.get(Listing, property_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Property not found")
    if session not in _favourites:
        _favourites[session] = []
    if property_id not in _favourites[session]:
        _favourites[session].append(property_id)
    return {"status": "added", "property_id": property_id}

@router.delete("/{property_id}")
async def remove_favourite(property_id: str, session: str = Depends(get_session)):
    if session in _favourites and property_id in _favourites[session]:
        _favourites[session].remove(property_id)
    return {"status": "removed", "property_id": property_id}
