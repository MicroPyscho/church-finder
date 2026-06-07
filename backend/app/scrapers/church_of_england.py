import asyncio
import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

PRICE_RE = re.compile(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?')
LOCATION_RE = re.compile(r'Location\s*:?\s*([^\n\.]+)', re.I)
DIOCESE_RE = re.compile(r'Diocese\s*(?:of)?\s*:?\s*([A-Za-z\s]+?)(?:\s+The|\s+Grade|\s+Location|\.|\n|,|$)', re.I)


def clean_coe_title(raw: str) -> str:
    """
    Extract just the church name from CoE accordion text.
    Input: "South Hylton Saint Mary (Diocese of Durham) The Grade II Listed..."
    Output: "South Hylton Saint Mary"
    """
    # Remove diocese parenthetical
    title = re.sub(r'\(Diocese[^)]*\)', '', raw)
    # Remove everything from "The Grade" onwards
    title = re.sub(r'\s+The\s+Grade.*', '', title, flags=re.I)
    # Remove "UNDER OFFER" etc
    title = re.sub(r'\b(UNDER OFFER|FOR SALE|SOLD|POA|ENQUIRE)\b.*', '', title, flags=re.I)
    # Remove offer price text that got concatenated
    title = re.sub(r'Offers?\s+(over|in excess|invited).*', '', title, flags=re.I)
    # Clean up whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Strip trailing punctuation
    title = title.rstrip('.,;:-')
    return title[:120]


class ChurchOfEnglandScraper(BaseScraper):
    source_name = "Church of England"
    source_type = "httpx"
    URLS = [
        "https://www.churchofengland.org/resources/parish-reorganisation-and-church-property/closed-churches/closed-church-buildings",
        "https://www.churchofengland.org/resources/property/churches-for-sale",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")

                items = soup.select(
                    ".accordion-item, .expandable, "
                    ".paragraph--type--detailed-accordion-element"
                )

                for item in items:
                    text = item.get_text(" ", strip=True)
                    if len(text) < 15:
                        continue
                    if not is_genuine_church("", text):
                        continue

                    # Get title from accordion heading
                    title_el = item.select_one(
                        "h2, h3, h4, button, summary, "
                        ".accordion-title, [class*=title]"
                    )
                    raw_title = title_el.get_text(strip=True) if title_el else text[:120]
                    title = clean_coe_title(raw_title)

                    if len(title) < 5:
                        continue

                    # Deduplicate by cleaned title
                    key = title.lower()[:40]
                    if key in seen:
                        continue
                    seen.add(key)

                    # Price
                    pm = PRICE_RE.search(text)
                    price = pm.group(0) if pm else "Enquire"

                    # Location — prefer explicit "Location:" field
                    location = "England"
                    loc_m = LOCATION_RE.search(text)
                    if loc_m:
                        location = loc_m.group(1).strip()[:60]
                    else:
                        dioc_m = DIOCESE_RE.search(text)
                        if dioc_m:
                            location = f"Diocese of {dioc_m.group(1).strip()}"[:60]

                    results.append(self.make_listing(
                        url=url,
                        title=title,
                        price_raw=price,
                        location=location,
                        description=text[:500],
                        property_type="church",
                    ))

            except Exception as e:
                self.logger.warning("CoE %s failed: %s", url, e)
            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
