import asyncio, re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

DIOCESE_RE = re.compile(r'Diocese(?:\s+of)?\s*:?\s*([A-Za-z\s]+?)(?:\s+Location|\s+The|\s+Grade|\.|,|$)', re.I)
LOCATION_RE = re.compile(r'Location\s*:?\s*([^,\n]+(?:,\s*[^,\n]+)?)', re.I)

class ChurchOfEnglandScraper(BaseScraper):
    source_name = "Church of England"
    source_type = "httpx"
    URLS = [
        "https://www.churchofengland.org/resources/parish-reorganisation-and-church-property/closed-churches/closed-church-buildings",
        "https://www.churchofengland.org/resources/property/churches-for-sale",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                items = soup.select(".accordion-item, .expandable, .paragraph--type--detailed-accordion-element")
                self.logger.info("CoE %s: %d accordion items", url.split("/")[-1], len(items))

                for item in items:
                    text = item.get_text(" ", strip=True)
                    if len(text) < 15: continue
                    if not is_genuine_church("", text): continue

                    title_el = item.select_one("h2, h3, h4, button, summary, .accordion-title, [class*=title]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    if len(title) < 5: continue

                    # Deduplicate by title
                    title_key = title[:40].lower()
                    if title_key in seen: continue
                    seen.add(title_key)

                    price = extract_price(text) or "Enquire"

                    # Extract clean location from text
                    location = "England"
                    loc_match = LOCATION_RE.search(text)
                    if loc_match:
                        location = loc_match.group(1).strip()[:60]
                    else:
                        dioc_match = DIOCESE_RE.search(text)
                        if dioc_match:
                            location = f"Diocese of {dioc_match.group(1).strip()}"[:60]

                    results.append(self.make_listing(
                        url=url, title=title, price_raw=price,
                        location=location, description=text[:500],
                        property_type="church",
                    ))

            except Exception as e:
                self.logger.warning("CoE %s failed: %s", url, e)
            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
