import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class AuctionHouseScraper(BaseScraper):
    source_name = "Auction House UK"
    source_type = "httpx"
    SEARCHES = [
        "https://auctionhouse.co.uk/?s=church",
        "https://auctionhouse.co.uk/?s=chapel",
        "https://auctionhouse.co.uk/?s=place+of+worship",
        "https://auctionhouse.co.uk/?s=former+church",
        "https://auctionhouse.co.uk/?s=gospel+hall",
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
                    "article, div[class*=property], div[class*=lot], "
                    "li[class*=result], div[class*=listing]"
                ):
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://auctionhouse.co.uk" + href
                    if href in seen:
                        continue
                    text = card.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title_el = card.select_one("h2, h3, h4, [class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="England", description=text[:400],
                        property_type=classify(text), listing_type="auction",
                    ))
            except Exception as e:
                self.logger.warning("AuctionHouse %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
