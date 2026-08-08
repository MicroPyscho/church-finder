import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify

class ChurchesConservationTrustScraper(BaseScraper):
    """
    Churches Conservation Trust — visitchurches.org.uk
    Manages 350+ historic churches. Conservation projects page
    signals churches at risk / in transition.
    """
    source_name = "Churches Conservation Trust"
    source_type = "httpx"
    URLS = [
        "https://www.visitchurches.org.uk/what-we-do/conservation/conservation-projects",
        ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for item in soup.select("article,div[class*=church],div[class*=project],div[class*=card],li[class*=church]"):
                    text = item.get_text(" ", strip=True)
                    if len(text) < 20: continue
                    link = item.select_one("a[href]")
                    if not link: continue
                    href = link.get("href", "")
                    if not href.startswith("http"): href = "https://www.visitchurches.org.uk" + href
                    if href in seen: continue
                    seen.add(href)
                    title_el = item.select_one("h2,h3,[class*=title],[class*=name]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    addr_el = item.select_one("[class*=location],[class*=address],[class*=county]")
                    location = addr_el.get_text(strip=True) if addr_el else "England"
                    results.append(self.make_listing(
                        url=href, title=title, price_raw="Heritage at Risk",
                        location=location, description=text[:400],
                        property_type="church", is_signal=True,
                        signal_type="heritage",
                    ))
            except Exception as e:
                self.logger.warning("CCT %s failed: %s", url, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
