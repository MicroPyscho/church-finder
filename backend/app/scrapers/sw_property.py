"""
SW Property — specialist ecclesiastical and community property agent.
Handles churches, chapels, halls, manses and other faith buildings.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class SWPropertyScraper(BaseScraper):
    source_name = "SW Property"
    source_type = "httpx"
    URLS = [
        "https://www.sw.co.uk/properties/?type=church",
        "https://www.sw.co.uk/properties/?type=chapel",
        "https://www.sw.co.uk/properties/?type=place-of-worship",
        "https://www.sw.co.uk/properties/?keyword=church",
        "https://www.sw.co.uk/properties/?keyword=chapel",
        "https://www.sw.co.uk/properties/?keyword=gospel+hall",
        "https://www.sw.co.uk/properties/?keyword=place+of+worship",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                if r.status_code != 200:
                    self.logger.debug("SW %s: %d", url, r.status_code)
                    continue

                soup = BeautifulSoup(r.text, "lxml")

                # SW uses standard property listing cards
                cards = soup.select(
                    "div[class*=property], article[class*=property], "
                    "li[class*=property], div[class*=listing]"
                )

                if not cards:
                    # Try generic article/card selectors
                    cards = soup.select("article, div[class*=card]")

                for card in cards:
                    link = card.select_one("a[href]")
                    if not link:
                        continue
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        href = "https://www.sw.co.uk" + href
                    # Must be a property URL
                    if "sw.co.uk" not in href:
                        continue
                    if href in seen:
                        continue

                    text = card.get_text(" ", strip=True)
                    if not is_genuine_church("", text):
                        continue

                    seen.add(href)

                    title_el = card.select_one("h2, h3, h4, [class*=title], [class*=address]")
                    title = title_el.get_text(strip=True) if title_el else text[:120]

                    price_el = card.select_one("[class*=price]")
                    price = price_el.get_text(strip=True) if price_el else extract_price(text) or "Enquire"

                    addr_el = card.select_one("[class*=address], [class*=location]")
                    location = addr_el.get_text(strip=True)[:80] if addr_el else "England"

                    img_el = card.select_one("img[src]")
                    image_url = img_el.get("src") if img_el else None
                    if image_url and not image_url.startswith("http"):
                        image_url = "https://www.sw.co.uk" + image_url

                    results.append(self.make_listing(
                        url=href,
                        title=title,
                        price_raw=price,
                        location=location,
                        description=text[:500],
                        property_type=classify(title + " " + text),
                        image_url=image_url,
                        images_json=[image_url] if image_url else [],
                    ))

            except Exception as e:
                self.logger.warning("SW Property %s: %s", url, e)
            await asyncio.sleep(1)

        # Also try the sitemap approach — fetch listings by URL pattern
        if not results:
            try:
                r = await client.get("https://www.sw.co.uk/properties/", timeout=20, follow_redirects=True)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    for a in soup.select("a[href*='/properties/']"):
                        href = a.get("href", "")
                        if not href.startswith("http"):
                            href = "https://www.sw.co.uk" + href
                        if href in seen or href == "https://www.sw.co.uk/properties/":
                            continue
                        text = a.get_text(strip=True)
                        if not is_genuine_church("", text) and not any(
                            kw in href.lower() for kw in ["church", "chapel", "worship", "gospel", "hall"]
                        ):
                            continue
                        seen.add(href)
                        results.append(self.make_listing(
                            url=href,
                            title=text[:120] or href.split("/")[-2].replace("-", " ").title(),
                            price_raw="Enquire",
                            location="England",
                            description=text[:400],
                            property_type="church",
                        ))
            except Exception as e:
                self.logger.warning("SW Property fallback: %s", e)

        self.log_result(len(results))
        return results
