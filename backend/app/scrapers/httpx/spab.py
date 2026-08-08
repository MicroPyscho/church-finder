"""
SPAB — Society for Protection of Ancient Buildings.
Lists historic and ancient church buildings seeking new use or sale.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

class SPABScraper(BaseScraper):
    source_name = "SPAB"
    source_type = "httpx"
    URLS = [
        "https://www.spab.org.uk/advice/find-a-building",
        "https://www.spab.org.uk/advice/buildings-at-risk",
        ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=15, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                for a in soup.select("a[href]"):
                    href = a.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.spab.org.uk" + href
                    if href in seen:
                        continue
                    text = a.get_text(strip=True)
                    parent = a.find_parent()
                    ctx = parent.get_text(" ", strip=True) if parent else text
                    if not is_genuine_church(text, ctx):
                        continue
                    if len(text) < 8:
                        continue
                    seen.add(href)
                    results.append(self.make_listing(
                        url=href, title=text[:120],
                        price_raw=extract_price(ctx) or "Enquire",
                        location="England", description=ctx[:400],
                        property_type="church",
                    ))
            except Exception as e:
                self.logger.warning("SPAB %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
