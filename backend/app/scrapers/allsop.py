import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class AllsopScraper(BaseScraper):
    source_name = "Allsop Auctions"
    source_type = "httpx"
    URLS = [
        "https://www.allsop.co.uk/auctions/residential-auctions/",
        "https://www.allsop.co.uk/auctions/commercial-auctions/",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for lot in soup.select("div.lot,article.lot,div[class*=lot],div[class*=property],li[class*=lot]"):
                    text = lot.get_text(" ",strip=True)
                    title_el = lot.select_one("h2,h3,[class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    if not is_genuine_church(title, text): continue
                    link = lot.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if href.startswith("/"): href = "https://www.allsop.co.uk" + href
                    price_el = lot.select_one("[class*=guide],[class*=price]")
                    addr_el  = lot.select_one("[class*=address],[class*=location]")
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=price_el.get_text(strip=True) if price_el else extract_price(text) or "TBC",
                        location=addr_el.get_text(strip=True) if addr_el else "England",
                        description=text[:400],
                        property_type=classify(title),
                        listing_type="auction",
                    ))
            except Exception as e:
                self.logger.warning("Allsop %s failed: %s", url, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
