"""
Savills Ecclesiastical — specialist church and religious building sales.
One of the UK's leading agents for ecclesiastical property.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class SavillsEcclesiasticalScraper(BaseScraper):
    source_name = "Savills"
    source_type = "httpx"
    SEARCHES = [
        "https://search.savills.com/list?Attributes=IsCommercial&SType=SSAL&SearchType=property&SortOrder=PriceDESC&keywordFilter=church",
        "https://search.savills.com/list?Attributes=IsCommercial&SType=SSAL&SearchType=property&keywordFilter=chapel",
        "https://search.savills.com/list?Attributes=IsCommercial&SType=SSAL&SearchType=property&keywordFilter=ecclesiastical",
        "https://search.savills.com/list?SType=SSAL&SearchType=property&keywordFilter=former+church",
        "https://search.savills.com/list?SType=SSAL&SearchType=property&keywordFilter=converted+chapel",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()
        for url in self.SEARCHES:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select(
                    "div[class*=property], article, li[class*=property], "
                    "div[data-testid*=property], div[class*=card]"
                ):
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://search.savills.com" + href
                    if href in seen:
                        continue
                    text = card.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title_el = card.select_one("h2, h3, [class*=title], [class*=address]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    addr_el = card.select_one("[class*=address], [class*=location]")
                    location = addr_el.get_text(strip=True)[:80] if addr_el else "England"
                    img_el = card.select_one("img[src]")
                    image_url = img_el.get("src") if img_el else None
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "POA",
                        location=location, description=text[:400],
                        property_type=classify(text),
                        image_url=image_url,
                        images_json=[image_url] if image_url else [],
                    ))
            except Exception as e:
                self.logger.warning("Savills %s: %s", url, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
