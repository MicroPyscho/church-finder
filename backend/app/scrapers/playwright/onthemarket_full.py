"""
OnTheMarket full scraper — requires Playwright.

OTM's Next.js app loads search results client-side. The __NEXT_DATA__
JSON block exists but only contains initial state, not full search results
when filters are applied. Playwright gets the full rendered output.

TODO: Implement using Playwright:
  1. Navigate to search URL
  2. Wait for li[data-testid='listing-card'] to appear
  3. Extract all listings, handling pagination
  4. Each card has address, price, description and image

Search terms to use (see CHURCH_KEYWORDS in base.py):
  former chapel, converted chapel, former church, methodist chapel,
  gospel hall, place of worship, church conversion, ecclesiastical
"""

# from app.scrapers.base import BaseScraper, ScrapedListing
# class OnTheMarketFullScraper(BaseScraper):
#     source_name = "OnTheMarket"
#     source_type = "playwright"
#     async def scrape(self, page) -> list[ScrapedListing]:
#         raise NotImplementedError("OnTheMarket full scraper requires Playwright")
