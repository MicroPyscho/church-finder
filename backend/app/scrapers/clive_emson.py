import asyncio, re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class CliveEmsonScraper(BaseScraper):
    source_name = "Clive Emson Auctions"
    source_type = "httpx"
    TERMS = ["church","chapel","cathedral","hall","former+church","former+chapel","place+of+worship","gospel+hall","ecclesiastical","community+hall","tabernacle","meeting+house","church+building","religious+building"]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for term in self.TERMS:
            url = f"https://www.cliveemson.co.uk/properties/?keyword={term}"
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for card in soup.select("div.lot"):
                    title    = card.get("data-cathead","").strip()
                    price    = card.get("data-price","").strip()
                    location = card.get("data-loc","").strip()
                    lot_num  = card.get("data-lot","")
                    auction  = card.get("data-auc","")
                    if not title or not is_genuine_church(title):
                        continue
                    if not price:
                        price = extract_price(card.get_text(" ",strip=True)) or "Nil Reserve"
                    if auction and lot_num:
                        href = f"https://www.cliveemson.co.uk/properties/{auction}/lot-{lot_num}/"
                    else:
                        link = card.select_one("a[href]")
                        href = link.get("href","") if link else ""
                        if href.startswith("/"): href = "https://www.cliveemson.co.uk" + href
                    if not href or href in seen:
                        continue
                    seen.add(href)

                    # Scrape the detail page for images
                    images = await self._get_images(client, href)

                    results.append(self.make_listing(
                        url=href, title=title, price_raw=price,
                        location=location or "South East",
                        description=card.get_text(" ",strip=True)[:400],
                        property_type=classify(title),
                        listing_type="auction",
                        image_url=images[0] if images else None,
                        images_json=images,
                    ))
            except Exception as e:
                self.logger.warning("Clive Emson %s failed: %s", term, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results

    async def _get_images(self, client, url: str) -> list[str]:
        try:
            r = await client.get(url, timeout=15, follow_redirects=True)
            if r.status_code != 200: return []
            soup = BeautifulSoup(r.text, "lxml")
            images = []
            # Clive Emson gallery images
            for img in soup.select("div.lot-gallery img, div.property-images img, img[class*=gallery], div[class*=slider] img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src","")
                if src and src.startswith("http") and src not in images:
                    images.append(src)
            # Also check og:image
            if not images:
                og = soup.find("meta", property="og:image")
                if og and og.get("content"):
                    images.append(og["content"])
            return images[:5]
        except:
            return []
