"""
Rightmove scraper — requires Playwright.

Rightmove uses React and loads all property data via internal API calls.
httpx only returns the shell HTML, not the property listings.

TODO: Implement using Playwright:
  1. Navigate to search URL
  2. Wait for div[data-test='results-count'] to appear
  3. Extract property cards from div[class*='propertyCard']
  4. Paginate through results

Search URLs to use:
  https://www.rightmove.co.uk/property-for-sale/search.html?keywords=former+chapel
  https://www.rightmove.co.uk/property-for-sale/search.html?keywords=converted+chapel
  https://www.rightmove.co.uk/property-for-sale/search.html?keywords=former+church
  https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=church
  https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=chapel
"""

# from app.scrapers.base import BaseScraper, ScrapedListing
# class RightmoveScraper(BaseScraper):
#     source_name = "Rightmove"
#     source_type = "playwright"
#     async def scrape(self, page) -> list[ScrapedListing]:
#         raise NotImplementedError("Rightmove requires Playwright worker")
