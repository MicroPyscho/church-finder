"""
OnTheMarket — Playwright scraper.
Results render server-side as /details/{id}/ links.
We collect links from search pages then visit each listing for full data.
"""
import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

SEARCH_TERMS = [
    "former+chapel",
    "converted+chapel",
    "former+church",
    "methodist+chapel",
    "place+of+worship",
    "gospel+hall",
    "church+conversion",
    "ecclesiastical",
]

BASE = "https://www.onthemarket.com"


class OnTheMarketFullScraper(BaseScraper):
    source_name = "OnTheMarket"
    source_type = "playwright"

    async def scrape(self, client=None) -> list[ScrapedListing]:
        from playwright.async_api import async_playwright
        results = []
        seen_urls = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Accept cookies once
            await page.goto(BASE, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(1500)
            for btn_text in ["Accept all", "Accept All", "Accept"]:
                try:
                    await page.click(f'button:has-text("{btn_text}")', timeout=2000)
                    break
                except:
                    continue
            await page.wait_for_timeout(500)

            # Collect detail links from each search term
            detail_links = set()
            for term in SEARCH_TERMS:
                try:
                    url = f"{BASE}/for-sale/property/uk/?keywords={term}"
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)
                    content = await page.content()
                    soup = BeautifulSoup(content, "lxml")
                    for a in soup.select("a[href*='/details/']"):
                        href = a.get("href", "")
                        if href and "/details/" in href:
                            full = BASE + href if href.startswith("/") else href
                            detail_links.add(full)
                    self.logger.info("OTM '%s': %d links so far", term, len(detail_links))
                except Exception as e:
                    self.logger.warning("OTM search %s: %s", term, e)
                await asyncio.sleep(2)

            self.logger.info("OTM: %d unique detail pages to visit", len(detail_links))

            # Visit each detail page
            for detail_url in list(detail_links)[:60]:  # cap at 60 per run
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
                try:
                    await page.goto(detail_url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(1500)
                    content = await page.content()
                    soup = BeautifulSoup(content, "lxml")

                    # Title / address
                    h1 = soup.select_one("h1")
                    title = h1.get_text(strip=True) if h1 else ""

                    # Must be a genuine church property
                    page_text = soup.get_text(" ", strip=True)
                    if not is_genuine_church(title, page_text):
                        continue

                    # Price
                    price_el = soup.select_one("[class*=price], h2[class*=price], p[class*=price]")
                    price = price_el.get_text(strip=True) if price_el else extract_price(page_text) or "POA"

                    # Location
                    loc_el = soup.select_one("[class*=address], [class*=location], h2")
                    location = loc_el.get_text(strip=True) if loc_el else title

                    # Description
                    desc_el = soup.select_one("[class*=description], [class*=about], article p")
                    description = desc_el.get_text(strip=True)[:500] if desc_el else page_text[:400]

                    # Images
                    imgs = []
                    for img in soup.select("img[src*='media.onthemarket'], img[src*='property']"):
                        src = img.get("src", "")
                        if src and src.startswith("http") and src not in imgs:
                            imgs.append(src)
                    imgs = imgs[:5]

                    results.append(self.make_listing(
                        url=detail_url,
                        title=title or location,
                        price_raw=price,
                        location=location,
                        description=description,
                        property_type=classify(title + " " + page_text[:200]),
                        image_url=imgs[0] if imgs else None,
                        images_json=imgs,
                    ))

                except Exception as e:
                    self.logger.debug("OTM detail %s: %s", detail_url, e)

                await asyncio.sleep(1)

            await browser.close()

        self.log_result(len(results))
        return results
