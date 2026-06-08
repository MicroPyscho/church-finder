"""
Paul Fosh Auctions — Wales auction house.
NOTE: Site currently shows "Coming Soon" — disabled until live.
"""
import asyncio
from app.scrapers.base import BaseScraper, ScrapedListing

class PaulFoshScraper(BaseScraper):
    source_name = "Paul Fosh Auctions"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        # Site not yet live — returns "Coming Soon" page
        self.logger.info("Paul Fosh: site not live, skipping")
        return []
