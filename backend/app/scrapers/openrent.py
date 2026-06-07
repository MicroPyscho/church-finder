import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class OpenRentScraper(BaseScraper):
    source_name = "OpenRent"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        for term in ["church+hall","former+chapel","community+hall"]:
            url = f"https://www.openrent.co.uk/properties-to-rent/?term={term}"
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select("div[class*=property],li[class*=property],[class*=listing]"):
                    text = card.get_text(" ",strip=True)
                    title_el = card.select_one("h2,h3,[class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    if not is_genuine_church(title, text): continue
                    link = card.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if href.startswith("/"): href = "https://www.openrent.co.uk" + href
                    price_el = card.select_one("[class*=price],[class*=pcm]")
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=price_el.get_text(strip=True) if price_el else extract_price(text) or "POA",
                        location="England",
                        description=text[:400],
                        property_type=classify(title),
                        listing_type="lease",
                    ))
            except Exception as e:
                self.logger.warning("OpenRent %s failed: %s", term, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
