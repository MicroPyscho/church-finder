"""
Rightmove — Playwright scraper.
Rightmove blocks httpx and API calls. Playwright renders the full page.
Uses the search page directly and extracts property cards from DOM.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

SEARCH_URLS = [
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=former+chapel&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=converted+chapel&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=former+church&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=church+conversion&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=place+of+worship&searchType=SALE",
    "https://www.rightmove.co.uk/property-for-sale/search.html?keywords=gospel+hall&searchType=SALE",
    "https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=church&searchType=SALE",
    "https://www.rightmove.co.uk/commercial-property-for-sale/search.html?keywords=chapel&searchType=SALE",
]


class RightmoveScraper(BaseScraper):
    source_name = "Rightmove"
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
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            for url in SEARCH_URLS:
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Accept cookies if present
                    for btn in ["Accept all cookies", "Accept all", "Accept"]:
                        try:
                            await page.click(f'button:has-text("{btn}")', timeout=1500)
                            await page.wait_for_timeout(500)
                            break
                        except:
                            continue

                    content = await page.content()
                    soup = BeautifulSoup(content, "lxml")

                    # Rightmove property cards
                    cards = soup.select(
                        "div[class*=propertyCard], l2[class*=propertyCard], "
                        "div[data-test*=property], article[class*=property]"
                    )
                    self.logger.info("Rightmove %s: %d cards", url.split("keywords=")[-1], len(cards))

                    for card in cards:
                        # Property URL
                        link = card.select_one("a[href*='/properties/']")
                        if not link:
                            continue
                        href = link.get("href", "")
                        if not href.startswith("http"):
                            href = "https://www.rightmove.co.uk" + href
                        # Remove query params for dedup
                        href_clean = href.split("?")[0]
                        if href_clean in seen:
                            continue

                        text = card.get_text(" ", strip=True)
                        if not is_genuine_church("", text):
                            continue

                        seen.add(href_clean)

                        # Address
                        addr_el = card.select_one(
                            "[class*=address], [data-test*=address], h2"
                        )
                        title = addr_el.get_text(strip=True) if addr_el else text[:120]

                        # Price
                        price_el = card.select_one(
                            "[class*=price], [data-test*=price]"
                        )
                        price = price_el.get_text(strip=True) if price_el else extract_price(text) or "POA"

                        # Image
                        img_el = card.select_one("img[src*='media.rightmove']")
                        image_url = img_el.get("src") if img_el else None

                        results.append(self.make_listing(
                            url=href,
                            title=title,
                            price_raw=price,
                            location=title,
                            description=text[:400],
                            property_type=classify(text),
                            image_url=image_url,
                            images_json=[image_url] if image_url else [],
                        ))

                except Exception as e:
                    self.logger.warning("Rightmove %s: %s", url.split("keywords=")[-1], e)
                await asyncio.sleep(3)

            await browser.close()

        self.log_result(len(results))
        return results
