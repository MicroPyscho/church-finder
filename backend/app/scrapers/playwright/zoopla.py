"""
Zoopla scraper — requires Playwright.

Zoopla is protected by Cloudflare and loads results client-side.
Requires stealth Playwright with human-like interaction.

TODO: Implement using rebrowser-playwright (already installed):
  1. Use stealth mode to bypass Cloudflare
  2. Navigate to search URL
  3. Wait for ul[data-testid='regular-listings'] to appear
  4. Extract property cards

Search URLs to use:
  https://www.zoopla.co.uk/for-sale/property/uk/?keywords=former+chapel
  https://www.zoopla.co.uk/for-sale/property/uk/?keywords=converted+church
  https://www.zoopla.co.uk/for-sale/property/uk/?keywords=place+of+worship
"""

# from app.scrapers.base import BaseScraper, ScrapedListing
# class ZooplaScraper(BaseScraper):
#     source_name = "Zoopla"
#     source_type = "playwright"
#     async def scrape(self, page) -> list[ScrapedListing]:
#         raise NotImplementedError("Zoopla requires Playwright with stealth")
