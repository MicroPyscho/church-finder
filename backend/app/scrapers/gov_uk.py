import asyncio
import json
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church

SEARCHES = [
    "https://www.gov.uk/search/all?keywords=church+property+disposal&order=updated-newest",
    "https://www.gov.uk/search/all?keywords=chapel+disposal+sale&order=updated-newest",
    "https://www.gov.uk/search/all?keywords=redundant+church+sale&order=updated-newest",
    "https://assets.publishing.service.gov.uk/",  # HMRC / government surplus
    "https://www.gov.uk/government/publications?departments%5B%5D=ministry-of-defence&keywords=church",
]

class GovUKScraper(BaseScraper):
    source_name = "GOV.UK"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in SEARCHES[:3]:  # Only search URLs
            try:
                r = await client.get(url, timeout=15, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")

                for item in soup.select("li.gem-c-document-list__item, div[class*=result], article"):
                    link = item.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.gov.uk" + href
                    if href in seen:
                        continue
                    text = item.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title = link.get_text(strip=True)[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw="Government disposal",
                        location="England", description=text[:400],
                        property_type="church", is_signal=True,
                        signal_type="government",
                    ))
            except Exception as e:
                self.logger.warning("GOV.UK %s: %s", url, e)
            await asyncio.sleep(1)

        self.log_result(len(results))
        return results
