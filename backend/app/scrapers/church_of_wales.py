import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, classify, extract_price

class ChurchOfWalesScraper(BaseScraper):
    source_name = "Church in Wales"
    source_type = "httpx"
    URLS = [
        "https://www.churchinwales.org.uk/en/about-us/representative-body/redundant-churches/",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.URLS:
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")

                # Church in Wales uses .block and .richtext-block classes
                # Find the main content area first
                content = soup.select_one("main, .main-content, #content, .content")
                if not content:
                    content = soup

                # Look in richtext blocks for church listings
                blocks = content.select(".richtext-block, .block, .section-title-block")
                self.logger.info("Church in Wales: %d blocks found", len(blocks))

                for block in blocks:
                    text = block.get_text(" ", strip=True)
                    if len(text) < 20: continue
                    if not any(kw in text.lower() for kw in ["church","chapel","redundant","available","sale","disposal"]): continue

                    # Find links to individual church pages
                    for a in block.select("a[href]"):
                        href = a.get("href","")
                        if not href.startswith("http"): href = "https://www.churchinwales.org.uk" + href
                        if href in seen: continue
                        seen.add(href)
                        link_text = a.get_text(strip=True)
                        if len(link_text) < 5: continue
                        surrounding = a.find_parent().get_text(" ",strip=True) if a.find_parent() else link_text
                        results.append(self.make_listing(
                            url=href, title=link_text,
                            price_raw=extract_price(surrounding) or "Enquire",
                            location="Wales",
                            description=surrounding[:400],
                            property_type="church",
                        ))

                # Also check for any table rows with church data
                for row in soup.select("table tr"):
                    cells = row.select("td")
                    if len(cells) < 2: continue
                    text = row.get_text(" ", strip=True)
                    if not any(kw in text.lower() for kw in ["church","chapel","available"]): continue
                    link = row.select_one("a[href]")
                    href = link.get("href","") if link else url
                    if not href.startswith("http"): href = "https://www.churchinwales.org.uk" + href
                    if href in seen: continue
                    seen.add(href)
                    title = cells[0].get_text(strip=True) if cells else text[:80]
                    results.append(self.make_listing(
                        url=href, title=title,
                        price_raw=extract_price(text) or "Enquire",
                        location="Wales", description=text[:400],
                        property_type="church",
                    ))

            except Exception as e:
                self.logger.warning("Church in Wales %s failed: %s", url, e)
            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
