import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class ChurchOfScotlandScraper(BaseScraper):
    source_name = "Church of Scotland"
    source_type = "httpx"
    URLS = [
        "https://www.churchofscotland.org.uk/about-us/departments/property-and-church-buildings/properties-for-sale",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for item in soup.select("article,div[class*=property],div[class*=listing],li[class*=property],div[class*=church],table tr"):
                    text = item.get_text(" ", strip=True)
                    if len(text) < 20: continue
                    if not is_genuine_church("", text): continue
                    link = item.select_one("a[href]")
                    if not link: continue
                    href = link.get("href", "")
                    if not href.startswith("http"): href = "https://www.churchofscotland.org.uk" + href
                    if href in seen: continue
                    seen.add(href)
                    title_el = item.select_one("h2,h3,td,[class*=title],[class*=name]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    price_el = item.select_one("[class*=price],[class*=offer],[class*=guide]")
                    addr_el  = item.select_one("[class*=location],[class*=address],[class*=area]")
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=price_el.get_text(strip=True) if price_el else extract_price(text) or "Enquire",
                        location=addr_el.get_text(strip=True) if addr_el else "Scotland",
                        description=text[:400],
                        property_type=classify(title + " " + text),
                    ))
            except Exception as e:
                self.logger.warning("Church of Scotland %s failed: %s", url, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
