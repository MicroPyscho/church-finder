import asyncio, json
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class OnTheMarketScraper(BaseScraper):
    source_name = "OnTheMarket"
    source_type = "httpx"
    SEARCHES = [
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=former+chapel",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=converted+chapel",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=former+church",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=methodist+chapel",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=church+conversion",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=place+of+worship",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=gospel+hall",
        "https://www.onthemarket.com/for-sale/property/uk/?keywords=ecclesiastical",
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        seen = set()

        for url in self.SEARCHES:
            try:
                r = await client.get(url, timeout=15, follow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "lxml")

                # OTM uses Next.js — extract JSON from __NEXT_DATA__
                nd = soup.find("script", {"id": "__NEXT_DATA__"})
                if nd and nd.string:
                    try:
                        data = json.loads(nd.string)
                        # Navigate to properties list
                        props = (
                            data.get("props", {})
                                .get("pageProps", {})
                                .get("searchResults", {})
                                .get("properties", [])
                        )
                        for p in props:
                            addr    = p.get("displayAddress", "").replace("\n", " ").strip()
                            summary = p.get("summary", "")
                            prop_url = "https://www.onthemarket.com" + p.get("propertyUrl", "")

                            if prop_url in seen:
                                continue
                            if not is_genuine_church(addr, summary):
                                continue
                            seen.add(prop_url)

                            # Price
                            price_data = p.get("price", {})
                            price_raw = "POA"
                            if price_data.get("displayPrices"):
                                price_raw = price_data["displayPrices"][0].get("displayPrice", "POA")

                            # Images
                            images_data = p.get("propertyImages", {})
                            imgs = []
                            if isinstance(images_data, dict):
                                main = images_data.get("mainImageSrc") or images_data.get("mainMapImageSrc")
                                if main:
                                    imgs = [main]
                                # Try images list
                                for img in images_data.get("images", []):
                                    src = img.get("srcUrl", "")
                                    if src and src not in imgs:
                                        imgs.append(src)
                            imgs = imgs[:5]

                            results.append(self.make_listing(
                                url=prop_url,
                                title=addr or summary[:120],
                                price_raw=price_raw,
                                location=addr,
                                description=summary[:400],
                                property_type=classify(addr + " " + summary),
                                image_url=imgs[0] if imgs else None,
                                images_json=imgs,
                            ))
                    except Exception as e:
                        self.logger.debug("OTM JSON parse %s: %s", url, e)
            except Exception as e:
                self.logger.warning("OTM %s: %s", url.split("=")[-1], e)
            await asyncio.sleep(2)

        self.log_result(len(results))
        return results
