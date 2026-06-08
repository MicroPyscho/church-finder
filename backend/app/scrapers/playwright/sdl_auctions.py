"""
SDL Auctions full scraper — requires Playwright.

SDL's search is AJAX-powered. The URL https://www.sdlauctions.co.uk/search/?q=church
returns a page shell; results load after JS execution.

TODO: Implement using Playwright:
  1. Navigate to https://www.sdlauctions.co.uk/search/?q=church
  2. Wait for div[class*='property-card'] or article to appear
  3. Extract title, price, location, image, URL

Also try: https://www.sdlauctions.co.uk/?s=church (WordPress search)
"""

# from app.scrapers.base import BaseScraper, ScrapedListing
# class SDLAuctionsFullScraper(BaseScraper):
#     source_name = "SDL Auctions"
#     source_type = "playwright"
#     async def scrape(self, page) -> list[ScrapedListing]:
#         raise NotImplementedError("SDL Auctions requires Playwright")
