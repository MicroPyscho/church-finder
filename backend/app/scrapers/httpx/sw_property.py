"""
SW Property — specialist ecclesiastical and community property agent.
"""
import asyncio
import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, classify, extract_price

# Must contain one of these to be a genuine church property
CHURCH_TERMS = [
    "church", "chapel", "ecclesiastical", "place of worship",
    "gospel hall", "meeting house", "tabernacle", "minster",
    "priory", "abbey","churches", "religious", "religion", "catholic", "anglican", "cathedral", "local church", "religious place", "place of gathering", "church hall", "vestry", "nave", "parish",
    "methodist", "baptist", "evangelical", "united reformed",
    "salvation army", "quaker", "citadel", "bethel",
]

# Reject if title is just a street address near a church
FALSE_POSITIVE_PATTERNS = re.compile(
    r'^\d+\s+\w+\s+(?:street|road|lane|avenue|close|court|place|way)\b'
    r'|^unit\s+\d+'
    r'|^land\s+to\s+the',
    re.IGNORECASE,
)

class SWPropertyScraper(BaseScraper):
    source_name = "SW Property"
    source_type = "httpx"
    URLS = [
        "https://www.sw.co.uk/properties/?keyword=church",
        "https://www.sw.co.uk/properties/?keyword=chapel",
        "https://www.sw.co.uk/properties/?keyword=place+of+worship",
        "https://www.sw.co.uk/properties/?keyword=gospel+hall",
        "https://www.sw.co.uk/properties/?keyword=ecclesiastical",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")
                cards = soup.select(
                    "div[class*=property], article[class*=property], "
                    "li[class*=property], div[class*=listing], article, div[class*=card]"
                )
                for card in cards:
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.sw.co.uk" + href
                    if "sw.co.uk" not in href or href in seen:
                        continue

                    text = card.get_text(" ", strip=True)
                    title_el = card.select_one("h2, h3, h4, [class*=title], [class*=address]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]

                    # Reject false positives
                    if FALSE_POSITIVE_PATTERNS.match(title):
                        continue

                    # Must have a church keyword in title or description
                    combined = (title + " " + text).lower()
                    if not any(t in combined for t in CHURCH_TERMS):
                        continue

                    seen.add(href)

                    price_el = card.select_one("[class*=price]")
                    price = price_el.get_text(strip=True) if price_el else extract_price(text) or "Enquire"

                    addr_el = card.select_one("[class*=address], [class*=location]")
                    location = addr_el.get_text(strip=True)[:80] if addr_el else "England"

                    img_el = card.select_one("img[src]")
                    image_url = img_el.get("src") if img_el else None
                    if image_url and not image_url.startswith("http"):
                        image_url = "https://www.sw.co.uk" + image_url

                    results.append(self.make_listing(
                        url=href, title=title, price_raw=price,
                        location=location, description=text[:500],
                        property_type=classify(title + " " + text),
                        image_url=image_url,
                        images_json=[image_url] if image_url else [],
                    ))
            except Exception as e:
                self.logger.warning("SW %s: %s", url, e)
            await asyncio.sleep(1)

        self.log_result(len(results))
        return results
