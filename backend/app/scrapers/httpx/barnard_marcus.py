import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class BarnardMarcusScraper(BaseScraper):
    source_name = "Barnard Marcus Auctions"
    source_type = "httpx"
    SEARCHES = [
        "https://www.barnardmarcus.co.uk/auctions/?q=church",
        "https://www.barnardmarcus.co.uk/auctions/?q=chapel",
        "https://www.barnardmarcus.co.uk/auctions/?q=place+of+worship",
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

                # Only pick up auction lot links — must contain /auctions/ in href
                for a in soup.select("a[href*='/auctions/']"):
                    href = a.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.barnardmarcus.co.uk" + href
                    # Skip search/nav pages
                    if href in seen or href == url:
                        continue
                    if not any(x in href for x in ["/lot/", "/lots/", "/property/", "/auction/"]):
                        continue

                    parent = a.find_parent()
                    text = parent.get_text(" ", strip=True) if parent else a.get_text(strip=True)

                    if not is_genuine_church("", text):
                        continue

                    seen.add(href)
                    title_el = (parent.select_one("h2, h3, [class*=title]") if parent else None)
                    title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True) or text[:120]

                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="London / South East",
                        description=text[:400],
                        property_type=classify(text),
                        listing_type="auction",
                    ))
            except Exception as e:
                self.logger.warning("BarnardMarcus %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results