import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class AllsopScraper(BaseScraper):
    source_name = "Allsop Auctions"
    source_type = "httpx"
    SEARCHES = [
        "https://www.allsop.co.uk/search/?q=church",
        "https://www.allsop.co.uk/search/?q=chapel",
        "https://www.allsop.co.uk/search/?q=place+of+worship",
        "https://www.allsop.co.uk/search/?q=former+church",
        "https://www.allsop.co.uk/search/?q=gospel+hall",
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

                # Find all links to individual property pages
                for a in soup.select("a[href]"):
                    href = a.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.allsop.co.uk" + href
                    # Allsop property URLs contain /lot/ or /property/
                    if not any(x in href for x in ["/lot/", "/property/", "/residential/", "/commercial/"]):
                        continue
                    if href in seen:
                        continue
                    text = a.get_text(" ", strip=True)
                    parent = a.find_parent()
                    parent_text = parent.get_text(" ", strip=True) if parent else text
                    if not is_genuine_church("", parent_text):
                        continue
                    seen.add(href)
                    results.append(self.make_listing(
                        url=href,
                        title=text[:120] or parent_text[:120],
                        price_raw=extract_price(parent_text) or "Enquire",
                        location="England",
                        description=parent_text[:400],
                        property_type=classify(parent_text),
                        listing_type="auction",
                    ))
            except Exception as e:
                self.logger.warning("Allsop %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
