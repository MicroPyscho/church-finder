"""
The Saleroom — auction aggregator covering UK and international auctions.
Includes ecclesiastical property and church contents/buildings.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class TheSaleRoomScraper(BaseScraper):
    source_name = "The Saleroom"
    source_type = "httpx"
    SEARCHES = [
        "https://www.the-saleroom.com/en-gb/auction-catalogues?q=church+building",
        "https://www.the-saleroom.com/en-gb/auction-catalogues?q=chapel+building",
        "https://www.the-saleroom.com/en-gb/auction-catalogues?q=ecclesiastical+property",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()
        for url in self.SEARCHES:
            try:
                r = await client.get(url, timeout=15, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select(
                    "div[class*=lot], article, li[class*=lot], "
                    "div[class*=result], div[class*=item]"
                ):
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.the-saleroom.com" + href
                    if href in seen:
                        continue
                    text = card.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title_el = card.select_one("h2, h3, [class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="England", description=text[:400],
                        property_type=classify(text), listing_type="auction",
                    ))
            except Exception as e:
                self.logger.warning("TheSaleRoom %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
