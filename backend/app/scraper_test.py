import asyncio, httpx, json, re
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-GB,en;q=0.9',
}

async def test_otm():
    """OnTheMarket — check if __NEXT_DATA__ has properties"""
    url = 'https://www.onthemarket.com/for-sale/property/kent/?keywords=church'
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
        r = await c.get(url, headers=HEADERS)
        print('OTM status:', r.status_code)
        soup = BeautifulSoup(r.text, 'lxml')
        nd = soup.find('script', {'id': '__NEXT_DATA__'})
        if nd and nd.string:
            try:
                data = json.loads(nd.string)
                pp = data.get('props', {}).get('pageProps', {})
                print('OTM pageProps keys:', list(pp.keys())[:10])
                for k, v in pp.items():
                    if isinstance(v, list) and len(v) > 0:
                        print(f'  List [{k}]: {len(v)} items')
                    elif isinstance(v, dict) and 'properties' in v:
                        print(f'  Dict [{k}] has properties: {len(v["properties"])}')
            except Exception as e:
                print('OTM parse error:', e)
        else:
            print('OTM: no __NEXT_DATA__')
            cards = soup.select('li[class*=property],div[class*=property-card],article')
            print(f'OTM HTML cards: {len(cards)}')
            if cards:
                print('First card text:', cards[0].get_text()[:200])

async def test_zoopla():
    """Zoopla — check structure"""
    url = 'https://www.zoopla.co.uk/for-sale/property/uk/?q=church+chapel'
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
        r = await c.get(url, headers=HEADERS)
        print('Zoopla status:', r.status_code)
        soup = BeautifulSoup(r.text, 'lxml')
        nd = soup.find('script', {'id': '__NEXT_DATA__'})
        if nd and nd.string:
            try:
                data = json.loads(nd.string)
                pp = data.get('props', {}).get('pageProps', {})
                print('Zoopla pageProps keys:', list(pp.keys())[:10])
                listings = pp.get('listings', pp.get('properties', pp.get('results', [])))
                if isinstance(listings, list):
                    print(f'Zoopla listings: {len(listings)}')
                    if listings:
                        print('First listing keys:', list(listings[0].keys())[:10])
                else:
                    for k, v in pp.items():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            print(f'  [{k}]: {len(v)} items, keys={list(v[0].keys())[:6]}')
            except Exception as e:
                print('Zoopla parse error:', e)
        else:
            print('Zoopla: no __NEXT_DATA__')

async def main():
    await test_otm()
    print()
    await test_zoopla()

asyncio.run(main())
