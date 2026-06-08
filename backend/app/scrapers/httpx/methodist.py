import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, extract_price

SALE_TERMS = [
    "for sale", "to let", "available", "disposal", "redundant",
    "surplus", "under offer", "freehold", "leasehold", "offers invited",
    "guide price", "auction",
]

class MethodistScraper(BaseScraper):
    source_name = "Methodist Church"
    source_type = "httpx"
    URLS = [
        "https://www.methodist.org.uk/for-churches/property/",
        "https://www.methodist.org.uk/for-churches/property/buying-and-selling/",
        "https://www.methodist.org.uk/for-churches/property/church-buildings-for-sale/",
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
                for item in soup.select(
                    "article, div[class*=property], div[class*=listing], "
                    "div[class*=content-item], li[class*=item]"
                ):
                    text = item.get_text(" ", strip=True)
                    if len(text) < 30:
                        continue
                    if not any(t in text.lower() for t in SALE_TERMS):
                        continue
                    link = item.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if href.startswith("/"):
                        href = "https://www.methodist.org.uk" + href
                    if href in seen:
                        continue
                    seen.add(href)
                    title_el = item.select_one("h2, h3, [class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="England", description=text[:400],
                        property_type="church",
                    ))
            except Exception as e:
                self.logger.warning("Methodist %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results