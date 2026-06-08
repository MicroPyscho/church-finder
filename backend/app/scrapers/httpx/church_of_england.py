import asyncio
import hashlib
import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

PRICE_RE    = re.compile(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?')
LOCATION_RE = re.compile(r'Location\s*:?\s*([^\n\.]{5,60})', re.I)
DIOCESE_RE  = re.compile(r'Diocese\s*(?:of)?\s*:?\s*([A-Za-z\s]+?)(?:\s+The|\s+Grade|\s+Location|\.|\n|,|$)', re.I)

def clean_title(raw: str) -> str:
    t = re.sub(r'\(Diocese[^)]*\)', '', raw)
    t = re.sub(r'\s+The\s+Grade.*', '', t, flags=re.I)
    t = re.sub(r'\b(UNDER OFFER|FOR SALE|SOLD|POA|ENQUIRE)\b.*', '', t, flags=re.I)
    t = re.sub(r'Offers?\s+(over|in excess|invited).*', '', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip().rstrip('.,;:-')
    return t[:120]

class ChurchOfEnglandScraper(BaseScraper):
    source_name = "Church of England"
    source_type = "httpx"
    URLS = [
        "https://www.churchofengland.org/resources/parish-reorganisation-and-church-property/closed-churches/closed-church-buildings",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen_titles = set()

        for page_url in self.URLS:
            try:
                r = await client.get(page_url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")

                items = soup.select(
                    ".accordion-item, .expandable, "
                    ".paragraph--type--detailed-accordion-element"
                )
                self.logger.info("CoE: %d accordion items", len(items))

                for item in items:
                    text = item.get_text(" ", strip=True)
                    if len(text) < 15 or not is_genuine_church("", text):
                        continue

                    title_el = item.select_one(
                        "h2, h3, h4, button, summary, .accordion-title, [class*=title]"
                    )
                    raw_title = title_el.get_text(strip=True) if title_el else text[:120]
                    title = clean_title(raw_title)
                    if len(title) < 5:
                        continue

                    key = title.lower()[:40]
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)

                    # Generate unique URL per listing using title hash
                    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50].strip('-')
                    unique_url = f"{page_url}#{slug}"

                    pm = PRICE_RE.search(text)
                    price = pm.group(0) if pm else "Enquire"

                    location = "England"
                    loc_m = LOCATION_RE.search(text)
                    if loc_m:
                        location = loc_m.group(1).strip()[:60]
                    else:
                        dioc_m = DIOCESE_RE.search(text)
                        if dioc_m:
                            location = f"Diocese of {dioc_m.group(1).strip()}"[:60]

                    results.append(self.make_listing(
                        url=unique_url,
                        title=title,
                        price_raw=price,
                        location=location,
                        description=text[:500],
                        property_type="church",
                    ))

            except Exception as e:
                self.logger.warning("CoE failed: %s", e)
            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
