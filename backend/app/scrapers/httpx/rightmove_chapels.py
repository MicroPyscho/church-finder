"""
Rightmove — church and chapel listings via their public search API.
Uses the JSON search endpoint (no Playwright needed for basic results).
"""
import asyncio
import json
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

SEARCHES = [
    "https://www.rightmove.co.uk/property-for-sale/search.html?searchType=SALE&keywords=church+conversion&locationIdentifier=USERDEFINEDAREA%5E%7B%22polylines%22%3A%22%22%7D&includeSSTC=false",
    "https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=church&searchType=SALE",
    "https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=chapel&searchType=SALE",
    "https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=place+of+worship&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=converted+chapel&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=former+church&searchType=SALE",
]

class RightmoveChapelsScraper(BaseScraper):
    source_name = "Rightmove"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in SEARCHES:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                if r.status_code != 200:
                    self.logger.warning("Rightmove %d: %s", r.status_code, url[:60])
                    continue

                soup = BeautifulSoup(r.text, "lxml")

                # Try JSON data first
                for script in soup.find_all("script"):
                    if script.string and "propertyData" in script.string:
                        try:
                            start = script.string.find("window.__PRELOADED_STATE__")
                            if start == -1:
                                continue
                            json_str = script.string[start:].split("=", 1)[1].strip().rstrip(";")
                            data = json.loads(json_str)
                            props = (data.get("results", {})
                                        .get("properties", []))
                            for p in props:
                                prop_url = "https://www.rightmove.co.uk" + p.get("propertyUrl", "")
                                if prop_url in seen:
                                    continue
                                summary = p.get("summary", "")
                                addr = p.get("displayAddress", "")
                                if not is_genuine_church(addr, summary):
                                    continue
                                seen.add(prop_url)
                                price = p.get("price", {}).get("displayPrices", [{}])[0].get("displayPrice", "POA")
                                imgs = []
                                if p.get("propertyImages", {}).get("images"):
                                    imgs = [img.get("srcUrl", "") for img in p["propertyImages"]["images"][:5] if img.get("srcUrl")]
                                results.append(self.make_listing(
                                    url=prop_url, title=addr or summary[:120],
                                    price_raw=price, location=addr,
                                    description=summary[:400],
                                    property_type=classify(addr + summary),
                                    image_url=imgs[0] if imgs else None,
                                    images_json=imgs,
                                ))
                        except Exception:
                            continue

                # HTML fallback
                for card in soup.select("div[class*=propertyCard], l2[class*=search-result]"):
                    link = card.select_one("a[href*='/properties/']")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.rightmove.co.uk" + href
                    if href in seen:
                        continue
                    text = card.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue
                    seen.add(href)
                    title_el = card.select_one("h2, [class*=address]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "POA",
                        location=title, description=text[:400],
                        property_type=classify(text),
                    ))

            except Exception as e:
                self.logger.warning("Rightmove %s: %s", url[:50], e)
            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
