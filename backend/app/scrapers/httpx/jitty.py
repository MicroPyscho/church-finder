import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class JittyScraper(BaseScraper):
    source_name = "Jitty"
    source_type = "httpx"
    URLS = [
        "https://jitty.com/for-sale/england/look-for-converted_church",
        "https://jitty.com/for-sale/england/look-for-chapel",
        "https://jitty.com/for-sale/england/look-for-church_hall",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select("div[class*=property],article,li[class*=property],[class*=listing]"):
                    text = card.get_text(" ",strip=True)
                    title_el = card.select_one("h2,h3,[class*=title],[class*=address]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    if not is_genuine_church(title, text): continue
                    link = card.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if not href.startswith("http"): href = "https://jitty.com" + href
                    if href in seen: continue
                    seen.add(href)
                    price_el = card.select_one("[class*=price]")
                    addr_el  = card.select_one("[class*=address],[class*=location]")
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=price_el.get_text(strip=True) if price_el else extract_price(text) or "POA",
                        location=addr_el.get_text(strip=True) if addr_el else "England",
                        description=text[:400],
                        property_type=classify(title),
                    ))
            except Exception as e:
                self.logger.warning("Jitty %s failed: %s", url, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
