# Test the __NEXT_DATA__ approach for Rightmove
import asyncio, httpx, json, re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.rightmove.co.uk/",
}

async def test():
    url = "https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=REGION%5E61&keywords=church&sortType=6"
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
        r = await c.get(url, headers=HEADERS)
        print("Status:", r.status_code)
        soup = BeautifulSoup(r.text, "lxml")

        # Method 1: __NEXT_DATA__ JSON
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script:
            print("Found __NEXT_DATA__")
            try:
                data = json.loads(script.string)
                # Navigate to properties
                props = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("searchPageProps", {})
                    .get("propertyCards", [])
                )
                print(f"Properties in __NEXT_DATA__: {len(props)}")
                if props:
                    p = props[0]
                    print("First property keys:", list(p.keys())[:10])
                    print("Sample:", p.get("displayAddress"), p.get("price", {}).get("displayPrices"))
            except Exception as e:
                print("Parse error:", e)
                print("__NEXT_DATA__ first 500 chars:", script.string[:500] if script.string else "empty")
        else:
            print("No __NEXT_DATA__ found")

        # Method 2: window.jsonModel
        for script in soup.find_all("script"):
            if script.string and "jsonModel" in (script.string or ""):
                print("Found jsonModel")
                m = re.search(r'jsonModel\s*=\s*({.+?});', script.string, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        props = data.get("properties", [])
                        print(f"Properties in jsonModel: {len(props)}")
                        if props:
                            print("First prop:", props[0].get("displayAddress"), props[0].get("price"))
                    except: pass
                break

asyncio.run(test())
