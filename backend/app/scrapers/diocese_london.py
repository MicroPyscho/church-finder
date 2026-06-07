import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify

class DioceseLondonScraper(BaseScraper):
    source_name = "Diocese of London"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        url = "https://www.london.anglican.org/articles/category/property/"
        try:
            r = await client.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("article,div[class*=post],div[class*=article]"):
                text = item.get_text(" ",strip=True)
                if not any(kw in text.lower() for kw in ["sale","disposal","available","property","church","chapel"]): continue
                link = item.select_one("a[href]")
                if not link: continue
                href = link.get("href","")
                if href.startswith("/"): href = "https://www.london.anglican.org" + href
                title_el = item.select_one("h2,h3,[class*=title]")
                title = title_el.get_text(strip=True) if title_el else text[:120]
                results.append(self.make_listing(
                    url=href, title=title, price_raw="Enquire",
                    location="London", description=text[:400],
                    property_type="church", is_signal=True,
                    signal_type="church_body",
                ))
        except Exception as e:
            self.logger.warning("Diocese London failed: %s", e)
        self.log_result(len(results))
        return results
