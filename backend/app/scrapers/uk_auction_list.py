import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class UKAuctionListScraper(BaseScraper):
    source_name = "UK Auction List"
    source_type = "httpx"
    TERMS = ["church","chapel","place+of+worship"]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        for term in self.TERMS:
            url = f"https://ukauctionlist.com/?s={term}"
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for item in soup.select("article,div.property,div.lot,li[class*=property]"):
                    text = item.get_text(" ",strip=True)
                    title_el = item.select_one("h2,h3,.entry-title,[class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    if not is_genuine_church(title, text): continue
                    link = item.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if href.startswith("/"): href = "https://ukauctionlist.com" + href
                    price_el = item.select_one("[class*=price],[class*=guide]")
                    addr_el  = item.select_one("[class*=address],[class*=location]")
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=price_el.get_text(strip=True) if price_el else extract_price(text) or "TBC",
                        location=addr_el.get_text(strip=True) if addr_el else "England",
                        description=text[:400],
                        property_type=classify(title),
                        listing_type="auction",
                    ))
            except Exception as e:
                self.logger.warning("UK Auction List %s failed: %s", term, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
