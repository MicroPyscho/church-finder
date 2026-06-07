import asyncio
import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, classify, extract_price


class AlexMartinScraper(BaseScraper):
    source_name = "Alex Martin Commercial"
    source_type = "httpx"
    URLS = [
        "https://alexmartin.co.uk/places-of-worship/",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")

                for container in soup.select("div.listing-container"):
                    # Find ONLY the real property URL — pattern: /properties/slug/
                    # Exclude mailto, social share, and add-to-compare links
                    real_link = None
                    for a in container.select("a[href]"):
                        href = a.get("href", "")
                        if (
                            "/properties/" in href
                            and "mailto" not in href
                            and "facebook" not in href
                            and "twitter" not in href
                            and "linkedin" not in href
                            and "whatsapp" not in href
                            and "pinterest" not in href
                            and "messenger" not in href
                            and href.startswith("https://alexmartin.co.uk/properties/")
                        ):
                            real_link = href
                            break

                    if not real_link or real_link in seen:
                        continue
                    seen.add(real_link)

                    # Location — the text link that shows "Barkingside, IG6" etc
                    location = ""
                    for a in container.select("a[href]"):
                        t = a.get_text(strip=True)
                        if t and "," in t and len(t) < 50 and not t.startswith("Add") and not t.startswith("View"):
                            location = t
                            break

                    # Image from background-image CSS
                    image_url = None
                    img_div = container.select_one(".listing-box-image")
                    if img_div:
                        style = img_div.get("style", "")
                        m = re.search(r"url\(['\"]?([^'\")\s]+)['\"]?\)", style)
                        if m:
                            src = m.group(1)
                            if src.startswith("http"):
                                image_url = src
                            elif src.startswith("/"):
                                image_url = "https://alexmartin.co.uk" + src

                    # Parse info lines for price, use type, size
                    price_raw = "POA"
                    use_type = "Place of Worship"
                    size = ""

                    for il in container.select(".info-line"):
                        key_el = il.select_one(".title")
                        val_el = il.select_one(".value")
                        if not key_el or not val_el:
                            continue
                        key = key_el.get_text(strip=True).lower().strip()
                        val = val_el.get_text(strip=True)
                        if not val:
                            continue
                        if key in ("price", "rent", "guide price", "asking price", "sale price"):
                            price_raw = val
                        elif key in ("use", "type", "property type", "use class"):
                            use_type = val
                        elif "sq" in key or "size" in key or "area" in key:
                            size = val

                    # Build a meaningful title
                    title = location if location else "Place of Worship"
                    if use_type and use_type.lower() not in title.lower():
                        title = f"{title} — {use_type}"
                    if size:
                        title += f" ({size})"

                    results.append(self.make_listing(
                        url=real_link,
                        title=title,
                        price_raw=price_raw,
                        location=location or "London",
                        description=container.get_text(" ", strip=True)[:400],
                        property_type=classify(use_type + " place of worship church"),
                        image_url=image_url,
                        images_json=[image_url] if image_url else [],
                    ))

            except Exception as e:
                self.logger.warning("Alex Martin %s failed: %s", url, e)

            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
