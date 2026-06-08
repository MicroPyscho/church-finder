import asyncio
import httpx
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, classify, extract_price

class ChurchGrowthTrustScraper(BaseScraper):
    source_name = "Church Growth Trust"
    source_type = "httpx"
    URLS = [
        "https://churchgrowth.org.uk/available-properties/",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.URLS:
            try:
                # SSL verify=False — their cert is self-signed
                async with httpx.AsyncClient(verify=False, timeout=20, follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}) as ssl_client:
                    r = await ssl_client.get(url)
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "lxml")

                    # Elementor CTA cards — .elementor-cta--skin-classic (9 found)
                    cards = soup.select(".elementor-cta--skin-classic, .elementor-cta, [class*=elementor-cta]")
                    self.logger.info("Church Growth Trust: %d elementor cards found", len(cards))

                    for card in cards:
                        text = card.get_text(" ", strip=True)
                        if len(text) < 10: continue
                        link = card.select_one("a[href]")
                        if not link:
                            link = card.find_parent("a")
                        if not link: continue
                        href = link.get("href","")
                        if not href.startswith("http"): href = "https://churchgrowth.org.uk" + href
                        if href in seen: continue
                        seen.add(href)

                        title_el = card.select_one(".elementor-cta__title, h2, h3, [class*=title], [class*=heading]")
                        title = title_el.get_text(strip=True) if title_el else text[:120]
                        desc_el = card.select_one(".elementor-cta__description, p, [class*=description]")
                        desc = desc_el.get_text(strip=True) if desc_el else text[:400]

                        results.append(self.make_listing(
                            url=href, title=title,
                            price_raw=extract_price(text) or "Enquire",
                            location="England", description=desc,
                            property_type=classify(title + " " + text),
                        ))

                    # Also check for any list items or posts
                    if not results:
                        for item in soup.select("article, .post, li[class*=property], div[class*=property]"):
                            text = item.get_text(" ", strip=True)
                            if len(text) < 10: continue
                            link = item.select_one("a[href]")
                            if not link: continue
                            href = link.get("href","")
                            if not href.startswith("http"): href = "https://churchgrowth.org.uk" + href
                            if href in seen: continue
                            seen.add(href)
                            title_el = item.select_one("h2,h3,[class*=title]")
                            title = title_el.get_text(strip=True) if title_el else text[:120]
                            results.append(self.make_listing(
                                url=href, title=title,
                                price_raw=extract_price(text) or "Enquire",
                                location="England", description=text[:400],
                                property_type=classify(title + " " + text),
                            ))

            except Exception as e:
                self.logger.warning("Church Growth Trust failed: %s", e)

        self.log_result(len(results))
        return results
