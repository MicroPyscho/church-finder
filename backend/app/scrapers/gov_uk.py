import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify

class GovUKScraper(BaseScraper):
    source_name = "GOV.UK"
    source_type = "httpx"
    QUERIES = ["surplus+church","church+disposal","place+of+worship+disposal"]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        for q in self.QUERIES:
            url = f"https://www.gov.uk/search/all?keywords={q}&order=updated-newest"
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for item in soup.select("li[class*=document],[class*=gem-c-document-list__item],div[class*=result]"):
                    text = item.get_text(" ",strip=True)
                    if not is_genuine_church("", text): continue
                    link = item.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if href.startswith("/"): href = "https://www.gov.uk" + href
                    title_el = item.select_one("h2,h3,[class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw="Government disposal", location="England",
                        description=text[:400],
                        property_type=classify(text),
                        is_signal=True, signal_type="gov_disposal",
                    ))
            except Exception as e:
                self.logger.warning("GOV.UK %s failed: %s", q, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
