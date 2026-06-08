import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing

DISPOSAL_TERMS = ["disposal","sale of property","church closure","property sale",
                  "surplus property","redundant building","faculty","pastoral measure"]

class CoESynodScraper(BaseScraper):
    source_name = "CoE Synod"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        url = "https://www.churchofengland.org/about/general-synod/papers-and-reports"
        try:
            r = await client.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("div[class*=document],li[class*=paper],article,div[class*=result]"):
                text = item.get_text(" ",strip=True)
                if not any(t in text.lower() for t in DISPOSAL_TERMS): continue
                link = item.select_one("a[href]")
                if not link: continue
                href = link.get("href","")
                if href.startswith("/"): href = "https://www.churchofengland.org" + href
                title_el = item.select_one("h2,h3,[class*=title]")
                title = title_el.get_text(strip=True) if title_el else text[:120]
                results.append(self.make_listing(
                    url=href, title=f"[AGM SIGNAL] {title[:100]}",
                    price_raw="Filing signal", location="England",
                    description=f"Synod paper with property disposal language. {text[:300]}",
                    property_type="church", is_signal=True, signal_type="agm",
                ))
        except Exception as e:
            self.logger.warning("CoE Synod failed: %s", e)
        self.log_result(len(results))
        return results
