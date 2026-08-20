"""
Barnard Marcus Auctions — specialist London auction house.
Discovers current auction dates from homepage, scrapes each
auction index page extracting lot tiles directly.
Only keeps church/chapel related lots.
Uses Crawl4AI for JS rendering.
"""
import re
import logging
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, extract_price

logger = logging.getLogger(__name__)

CHURCH_KEYWORDS = [
    "church", "chapel", "worship", "ecclesiast", "gospel hall",
    "methodist", "baptist", "vestry", "tabernacle", "congregational",
    "salvation army", "kingdom hall", "former church", "place of worship",
]

class BarnardMarcusScraper(BaseScraper):
    source_name = "Barnard Marcus Auctions"
    source_type = "httpx"
    BASE = "https://www.barnardmarcusauctions.co.uk"

    async def scrape(self, client) -> list[ScrapedListing]:
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("crawl4ai not installed — skipping Barnard Marcus")
            return []

        results = []
        seen = set()
        browser_config = BrowserConfig(headless=True)

        async with AsyncWebCrawler(config=browser_config, verbose=False) as crawler:

            # Step 1: get current auction URLs from homepage
            try:
                home = await crawler.arun(
                    url=self.BASE + "/",
                    config=CrawlerRunConfig(delay_before_return_html=3.0, page_timeout=20000)
                )
                # Find dated auction URLs e.g. /auctions/10-september-2026/
                auction_urls = list(dict.fromkeys(re.findall(
                    r'https://www\.barnardmarcusauctions\.co\.uk/auctions/\d+-[a-z]+-\d{4}/',
                    home.markdown or ""
                )))
                logger.info("Barnard Marcus: %d auction pages found", len(auction_urls))
            except Exception as e:
                logger.warning("Barnard Marcus homepage error: %s", e)
                return []

            # Step 2: scrape each auction index page
            for auction_url in auction_urls[:3]:
                try:
                    page = await crawler.arun(
                        url=auction_url,
                        config=CrawlerRunConfig(delay_before_return_html=5.0, page_timeout=30000)
                    )
                    soup = BeautifulSoup(page.html or "", "lxml")

                    # Find all lot tiles — each is a link containing lot info
                    lot_tiles = soup.select("a[href*='/auctions/']")

                    for tile in lot_tiles:
                        href = tile.get("href", "")
                        # Only individual lot URLs e.g. /auctions/10-september-2026/712345/
                        if not re.match(r'.*/auctions/[\d]+-\w+-\d{4}/\d+/', href):
                            continue

                        lot_url = href if href.startswith("http") else self.BASE + href
                        if lot_url in seen:
                            continue

                        tile_text = tile.get_text(" ", strip=True).lower()

                        # Filter: only church/chapel lots
                        if not any(kw in tile_text for kw in CHURCH_KEYWORDS):
                            continue

                        seen.add(lot_url)

                        # Extract title — first non-empty text block
                        full_text = tile.get_text(" ", strip=True)
                        lines = [l.strip() for l in full_text.split("  ") if l.strip()]

                        title = next((l for l in lines if len(l) > 5 and "lot" not in l.lower()[:4]), full_text[:80])
                        title = title[:120]

                        # Extract price
                        price_match = re.search(r'£[\d,]+', full_text)
                        price_raw = price_match.group(0) if price_match else "Auction"

                        # Extract address — lines that look like addresses
                        address_lines = [l for l in lines if re.search(r'\b[A-Z]{1,2}\d', l) or "," in l]
                        location = address_lines[0] if address_lines else "London"

                        if not title or not is_genuine_church(title + " " + tile_text):
                            continue

                        results.append(ScrapedListing(
                            id=self._make_id(lot_url),
                            source=self.source_name,
                            title=title,
                            price_raw=price_raw,
                            location=location,
                            url=lot_url,
                            description=full_text[:500],
                            images_json=[],
                        ))
                        logger.info("Barnard Marcus: ✓ %s", title[:60])

                except Exception as e:
                    logger.warning("Barnard Marcus %s error: %s", auction_url, e)

        logger.info("Barnard Marcus total: %d church listings", len(results))
        return results