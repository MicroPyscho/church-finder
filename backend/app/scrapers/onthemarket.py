import asyncio, json
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, is_genuine_church, classify, extract_price

class OnTheMarketScraper(BaseScraper):
    source_name = 'OnTheMarket'
    source_type = 'httpx'
    SEARCHES = [
        'https://www.onthemarket.com/for-sale/property/uk/?keywords=former+chapel',
        'https://www.onthemarket.com/for-sale/property/uk/?keywords=converted+chapel',
        'https://www.onthemarket.com/for-sale/property/uk/?keywords=former+church+for+sale',
        'https://www.onthemarket.com/for-sale/property/uk/?keywords=methodist+chapel+for+sale',
        'https://www.onthemarket.com/for-sale/property/uk/?keywords=church+conversion+for+sale',
    ]

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []; seen = set()
        for url in self.SEARCHES:
            try:
                r = await client.get(url, timeout=15, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'lxml')
                nd = soup.find('script', {'id': '__NEXT_DATA__'})
                if nd and nd.string:
                    try:
                        data = json.loads(nd.string)
                        props = (data.get('props',{}).get('pageProps',{})
                                 .get('searchResults',{}).get('properties',[]))
                        for p in props:
                            addr = p.get('displayAddress','').replace('\n',' ').strip()
                            summary = p.get('summary','')
                            prop_url = 'https://www.onthemarket.com' + p.get('propertyUrl','')
                            if prop_url in seen: continue
                            # Strict check — title AND description must indicate a church building
                            if not is_genuine_church(addr, summary): continue
                            seen.add(prop_url)
                            price_data = p.get('price',{})
                            price_raw = 'POA'
                            if price_data.get('displayPrices'):
                                price_raw = price_data['displayPrices'][0].get('displayPrice','POA')
                            images_data = p.get('propertyImages',{})
                            image_url = None
                            images = []
                            if isinstance(images_data, dict):
                                image_url = images_data.get('mainImageSrc') or images_data.get('mainMapImageSrc')
                                if image_url:
                                    images = [image_url]
                            results.append(self.make_listing(
                                url=prop_url, title=addr or summary[:120],
                                price_raw=price_raw, location=addr,
                                description=summary[:400],
                                property_type=classify(addr+' '+summary),
                                image_url=image_url,
                                images_json=images,
                            ))
                    except Exception as e:
                        self.logger.debug('OTM JSON: %s', e)
            except Exception as e:
                self.logger.warning('OTM %s: %s', url.split('=')[-1], e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
