"""
Historic England — Heritage at Risk register and grant-aided buildings.
Lists historic churches at risk, some available for new ownership.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

class HistoricEnglandScraper(BaseScraper):
    source_name = "Historic England"
    source_type = "httpx"
    URLS = [
        "https://historicengland.org.uk/advice/heritage-at-risk/search-register/?htype=place-of-worship",
        "https://historicengland.org.uk/listing/the-list/results/?htype=LB&searchType=nhle&q=chapel",
        "https://historicengland.org.uk/advice/heritage-at-risk/",
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
                for card in soup.select(
                    "div[class*=result], article, li[class*=item], "
                    "div[class*=listing], div[class*=card]"
                ):
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://historicengland.org.uk" + href
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
                        price_raw="Heritage at Risk",
                        location="England", description=text[:400],
                        property_type="church", is_signal=True,
                    ))
            except Exception as e:
                self.logger.warning("HistoricEngland %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
