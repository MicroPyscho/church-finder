import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing

class ChurchTimesScraper(BaseScraper):
    source_name = "Church Times"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        url = "https://www.churchtimes.co.uk/topics/church-buildings"
        try:
            r = await client.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("article,div[class*=article],[class*=story]")[:20]:
                text = item.get_text(" ",strip=True)
                if not any(s in text.lower() for s in ["sale","sold","disposal","auction","building","closure"]): continue
                link = item.select_one("a[href]")
                if not link: continue
                href = link.get("href","")
                if href.startswith("/"): href = "https://www.churchtimes.co.uk" + href
                title_el = item.select_one("h2,h3,[class*=title],[class*=headline]")
                title = title_el.get_text(strip=True) if title_el else text[:120]
                results.append(self.make_listing(
                    url=href, title=title, price_raw="See article",
                    location="England", description=text[:400],
                    property_type="church", is_signal=True,
                    signal_type="publication",
                ))
        except Exception as e:
            self.logger.warning("Church Times failed: %s", e)
        self.log_result(len(results))
        return results
