import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church

class PlanningSignalScraper(BaseScraper):
    source_name = "Planning Portal"
    source_type = "httpx"
    QUERIES = [
        "church+change+of+use",
        "chapel+residential+conversion",
        "place+of+worship+change+of+use",
        "community+hall+change+of+use",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        for q in self.QUERIES:
            url = f"https://www.planningportal.co.uk/applications?keyword={q}&status=submitted"
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                if r.status_code != 200: continue
                soup = BeautifulSoup(r.text, "lxml")
                for item in soup.select("div[class*=application],li[class*=application],tr[class*=application]"):
                    text = item.get_text(" ",strip=True)
                    if not is_genuine_church("", text): continue
                    link = item.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if href.startswith("/"): href = "https://www.planningportal.co.uk" + href
                    addr_el = item.select_one("[class*=address],[class*=location],[class*=site]")
                    results.append(self.make_listing(
                        url=href,
                        title=f"[PLANNING SIGNAL] {text[:100]}",
                        price_raw="Planning stage",
                        location=addr_el.get_text(strip=True) if addr_el else "England",
                        description=f"Planning application — property may come to market soon. {text[:300]}",
                        property_type="church", is_signal=True, signal_type="planning",
                    ))
            except Exception as e:
                self.logger.warning("Planning Portal %s failed: %s", q, e)
            await asyncio.sleep(3)
        self.log_result(len(results))
        return results
