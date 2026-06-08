import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

class DioceseLondonScraper(BaseScraper):
    source_name = "Diocese of London"
    source_type = "httpx"
    URLS = [
        "https://www.london.anglican.org/articles/property/",
        "https://www.london.anglican.org/articles/church-buildings-for-sale/",
        "https://www.london.anglican.org/mission/church-buildings/buildings-for-sale/",
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
                for item in soup.select("article, div[class*=property], div[class*=listing], div[class*=card]"):
                    link = item.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.london.anglican.org" + href
                    if href in seen:
                        continue
                    text = item.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title_el = item.select_one("h2, h3, h4, [class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="London", description=text[:400],
                        property_type="church",
                    ))
            except Exception as e:
                self.logger.warning("Diocese London %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
