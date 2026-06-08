"""
Church in Wales — JS-rendered, moved to playwright/church_of_wales.py
Returns no real listings via httpx — disabled to avoid false positives.
"""
import asyncio
from app.scrapers.base import BaseScraper, ScrapedListing

class ChurchOfWalesScraper(BaseScraper):
    source_name = "Church in Wales"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        self.logger.info("Church in Wales: JS-rendered, requires Playwright — skipping")
        return []
