"""
BTG Eddisons Auctions — Playwright scraper.
Properties load via JavaScript. Uses .property-card selector.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

SEARCH_TERMS = [
    "church", "chapel", "place+of+worship", "gospel+hall",
    "ecclesiastical", "cathedral", "old+church", "religious+place", "christian",  "former+church", "former+chapel",
    "tabernacle", "meeting+house",
]

class BTGEddisonsScraper(BaseScraper):
    source_name = "BTG Eddisons Auctions"
    source_type = "playwright"

    async def scrape(self, client=None) -> list[ScrapedListing]:
        from playwright.async_api import async_playwright
        results = []
        seen = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            })

            for term in SEARCH_TERMS:
                try:
                    url = f"https://www.btgeddisonspropertyauctions.com/properties?keyword={term}"
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    content = await page.content()
                    soup = BeautifulSoup(content, "lxml")

                    for card in soup.select(".property-card"):
                        # URL from the aria-label link
                        link = card.select_one("a[href*='/properties/']")
                        if not link:
                            continue
                        href = link.get("href", "")
                        if not href.startswith("http"):
                            href = "https://www.btgeddisonspropertyauctions.com" + href
                        if href in seen:
                            continue

                        text = card.get_text(" ", strip=True)
                        title = link.get("aria-label", "") or text[:120]

                        if not is_genuine_church(title, text):
                            continue

                        seen.add(href)

                        # Price
                        price_el = card.select_one("[class*=price], [class*=guide]")
                        price = price_el.get_text(strip=True) if price_el else extract_price(text) or "Enquire"

                        # Location from aria-label (format: "Address, Town, County Postcode")
                        location = title
                        if "," in title:
                            parts = title.split(",")
                            location = ", ".join(parts[-2:]).strip() if len(parts) >= 2 else title

                        # Images from swiper
                        imgs = []
                        for img in card.select("img[src]"):
                            src = img.get("src", "")
                            if src and src.startswith("http") and "placeholder" not in src:
                                imgs.append(src)

                        results.append(self.make_listing(
                            url=href,
                            title=title,
                            price_raw=price,
                            location=location,
                            description=text[:400],
                            property_type=classify(title + " " + text),
                            listing_type="auction",
                            image_url=imgs[0] if imgs else None,
                            images_json=imgs[:5],
                        ))

                    await asyncio.sleep(2)

                except Exception as e:
                    self.logger.warning("BTG %s: %s", term, e)

            await browser.close()

        self.log_result(len(results))
        return results
