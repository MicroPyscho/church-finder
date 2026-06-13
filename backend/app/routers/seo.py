"""
SEO router — sitemap, robots.txt, llms.txt, structured data.
Crawled by Google, Bing, and AI crawlers (GPTBot, Claude-Web, Gemini, PerplexityBot).
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Listing

router = APIRouter(tags=["seo"])
logger = logging.getLogger(__name__)

SITE_URL = "https://sanctuary.church"


@router.get("/robots.txt", include_in_schema=False)
async def robots():
    content = f"""User-agent: *
Allow: /
Allow: /properties/
Allow: /churches-for-sale/
Disallow: /api/
Disallow: /admin/

User-agent: GPTBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Gemini
Allow: /

User-agent: Googlebot
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Listing.id, Listing.last_seen).where(Listing.is_active == True)
    )).all()

    urls = []

    static = [
        ("", "1.0", "daily"),
        ("/churches-for-sale", "0.9", "daily"),
        ("/churches-for-sale/london", "0.9", "weekly"),
        ("/churches-for-sale/yorkshire", "0.9", "weekly"),
        ("/churches-for-sale/kent", "0.9", "weekly"),
        ("/churches-for-sale/surrey", "0.9", "weekly"),
        ("/churches-for-sale/midlands", "0.9", "weekly"),
        ("/churches-for-sale/manchester", "0.9", "weekly"),
        ("/churches-for-sale/wales", "0.9", "weekly"),
        ("/churches-for-sale/scotland", "0.9", "weekly"),
        ("/churches-for-sale/devon", "0.9", "weekly"),
        ("/churches-for-sale/lancashire", "0.9", "weekly"),
    ]

    for path, priority, freq in static:
        urls.append(f"""  <url>
    <loc>{SITE_URL}{path}</loc>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>""")

    for listing_id, last_seen in rows:
        lastmod = (last_seen or datetime.utcnow()).strftime("%Y-%m-%d")
        urls.append(f"""  <url>
    <loc>{SITE_URL}/properties/{listing_id}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    content = f"""# Sanctuary

> UK's most comprehensive search engine for churches, chapels, and places of worship for sale.

Sanctuary aggregates church and chapel property listings from auction houses, estate agents, ecclesiastical bodies, and conservation trusts across the United Kingdom.

## What we list

- Former churches and chapels for sale or auction
- Places of worship available for community use
- Listed ecclesiastical buildings with development potential
- Methodist, Baptist, Anglican, Catholic and non-denominational properties
- Properties across all UK regions including London, Yorkshire, Kent, Surrey, Wales and Scotland

## Search capabilities

Natural language search by location (proximity-aware), price range, denomination, building features (parking, graveyard, hall, spire), and size in square feet.

## Data sources

Alex Martin Commercial, Church of England, Churches Conservation Trust, Clive Emson Auctions, BTG Eddisons, SW Property, Savills Ecclesiastical, SDL Auctions, and 20+ other UK sources updated every 3 hours.

## Key pages

- {SITE_URL} — Main search
- {SITE_URL}/churches-for-sale — Browse all listings
- {SITE_URL}/sitemap.xml — Full sitemap
"""
    return Response(content=content, media_type="text/plain")


@router.get("/api/listings/{listing_id}/schema")
async def listing_schema(listing_id: str, db: AsyncSession = Depends(get_db)):
    listing = await db.get(Listing, listing_id)
    if not listing:
        return Response(status_code=404)

    images = []
    try:
        images = json.loads(listing.images) if listing.images else []
    except Exception:
        pass

    schema = {
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": listing.title,
        "description": (listing.description or "")[:500],
        "url": f"{SITE_URL}/properties/{listing.id}",
        "datePosted": listing.first_seen.isoformat() if listing.first_seen else None,
        "image": images[:3],
        "offers": {
            "@type": "Offer",
            "price": listing.price,
            "priceCurrency": "GBP",
            "availability": "https://schema.org/InStock" if listing.is_active else "https://schema.org/Discontinued",
        },
        "address": {
            "@type": "PostalAddress",
            "addressLocality": listing.location,
            "addressCountry": "GB",
        },
        "additionalType": "https://schema.org/Church",
        "provider": {
            "@type": "Organization",
            "name": listing.source,
        },
    }

    if listing.lat and listing.lon:
        schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude":  listing.lat,
            "longitude": listing.lon,
        }

    return schema
