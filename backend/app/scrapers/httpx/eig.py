"""
EIG Property Auctions — Essential Information Group.
Major UK auction platform aggregating lots from many auction houses.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class EIGScraper(BaseScraper):
    source_name = "EIG Property Auctions"
    source_type = "httpx"
    SEARCHES = [
        "https://www.eigroup.co.uk/property-auctions/results/?search=church",
        "https://www.eigroup.co.uk/property-auctions/results/?search=chapel",
        "https://www.eigroup.co.uk/property-auctions/results/?search=place+of+worship",
        "https://www.eigroup.co.uk/property-auctions/results/?search=former+church",
        "https://www.eigroup.co.uk/property-auctions/results/?search=gospel+hall",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()
        for url in self.SEARCHES:
            try:
                r = await client.get(url, timeout=15, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select(
                    "div[class*=property], article, tr[class*=lot], "
                    "li[class*=result], div[class*=lot]"
                ):
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.eigroup.co.uk" + href
                    if href in seen:
                        continue
                    text = card.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title_el = card.select_one("h2, h3, [class*=title], [class*=address]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    img_el = card.select_one("img[src]")
                    image_url = img_el.get("src") if img_el else None
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="England", description=text[:400],
                        property_type=classify(text), listing_type="auction",
                        image_url=image_url,
                        images_json=[image_url] if image_url else [],
                    ))
            except Exception as e:
                self.logger.warning("EIG %s: %s", url, e)
            await asyncio.sleep(1)
        self.log_result(len(results))
        return results
