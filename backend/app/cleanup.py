import asyncio
from app.database import AsyncSessionLocal
from app.models import Listing
from sqlalchemy import select, delete

CHURCH_KEYWORDS = [
    "church","chapel","ecclesiastical","vestry","nave","place of worship",
    "tabernacle","minster","priory","abbey","meeting house","mission hall",
    "former church","methodist","baptist","gospel hall","kingdom hall",
    "village hall","community hall","assembly hall","masonic hall",
    "memorial hall","drill hall","civic hall","parish hall",
    "former theatre","former cinema","bingo hall","former school",
    "graveyard","churchyard","presbytery","converted chapel",
    "converted church","church conversion",
]

COFE_BAD_TITLES = [
    "Hyde Park Estate sales and lettings",
    "Parish reorganisation and church property",
    "Mission, Pastoral & Church Property Committee",
    "Resources for churches",
    "Residential properties on the Hyde Park Estate",
    "Church resources",
    "Resourcing Church Administration",
    "Commercial Properties on the Hyde Park Estate",
    "Legacy resources for your church",
    "Resources for regular maintenance",
    "LLF resources",
    "Resources",
    "Churches, housing and building back better",
    "Give what you have in your hand to Jesus",
]

def is_genuine_church(title: str, description: str = "") -> bool:
    combined = (title + " " + description).lower()
    return any(kw in combined for kw in CHURCH_KEYWORDS)

async def clean():
    async with AsyncSessionLocal() as db:
        # Get all listings
        all_rows = (await db.execute(select(Listing))).scalars().all()
        to_delete = []

        for listing in all_rows:
            should_delete = False

            # Delete bad Church of England nav/article pages
            if listing.source == "Church of England":
                if listing.title in COFE_BAD_TITLES:
                    should_delete = True
                elif not is_genuine_church(listing.title, listing.description or ""):
                    should_delete = True

            # Delete Rightmove false positives (houses on Church Street etc)
            elif listing.source == "Rightmove":
                if not is_genuine_church(listing.title, listing.description or ""):
                    should_delete = True
                # Also delete ones where title starts with pipe chars (UI artifacts)
                elif listing.title.startswith("| ") or listing.title.startswith("| |"):
                    should_delete = True

            # Delete OnTheMarket false positives
            elif listing.source == "OnTheMarket":
                if not is_genuine_church(listing.title, listing.description or ""):
                    should_delete = True

            if should_delete:
                to_delete.append(listing.id)
                print(f"DELETE [{listing.source}] {listing.title[:60]}")

        # Delete them
        for lid in to_delete:
            listing = await db.get(Listing, lid)
            if listing:
                await db.delete(listing)

        await db.commit()

        # Count remaining
        remaining = (await db.execute(select(Listing))).scalars().all()
        print(f"\nDeleted {len(to_delete)} listings")
        print(f"Remaining: {len(remaining)} listings")
        for l in remaining:
            print(f"  [{l.source}] {l.title[:55]}")

asyncio.run(clean())
