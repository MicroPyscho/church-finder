import asyncio, httpx, json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.rightmove.co.uk/",
}

PLACES = ["Kent", "Surrey", "Hampshire", "Yorkshire", "Lancashire",
          "Devon", "Somerset", "Norfolk", "Essex", "Suffolk",
          "Gloucestershire", "Oxfordshire", "Wiltshire", "Berkshire",
          "Derbyshire", "Nottinghamshire", "Staffordshire", "Lincolnshire"]

async def get_location_id(client, place):
    chars = "/".join(list(place.upper()))
    url = f"https://www.rightmove.co.uk/typeAhead/uknostreet/{chars}"
    try:
        r = await client.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            items = data.get("typeAheadLocations", [])
            for item in items:
                lid = item.get("locationIdentifier", "")
                name = item.get("displayName", "")
                if "REGION" in lid:
                    print(f"  {place} -> {lid} ({name})")
                    return lid
    except Exception as e:
        print(f"  {place} error: {e}")
    return None

async def test_search(client, location_id, label):
    url = f"https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier={location_id}&keywords=church&sortType=6"
    r = await client.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "lxml")
    for s in soup.find_all("script"):
        src = s.string or ""
        if len(src) > 50000:
            try:
                data = json.loads(src)
                props = data["props"]["pageProps"]["searchResults"]["properties"]
                church_props = [p for p in props if any(
                    kw in (p.get("summary","") + p.get("displayAddress","")).lower()
                    for kw in ["church","chapel","ecclesiastical","vestry","place of worship","methodist","baptist"]
                )]
                print(f"  {label}: {len(props)} total, {len(church_props)} church-related")
                for p in church_props[:2]:
                    addr = p.get("displayAddress","").replace("\n", " ")
                    price = p.get("price",{}).get("displayPrices",[{}])[0].get("displayPrice","POA")
                    print(f"    - {addr} | {price}")
                return church_props
            except Exception as e:
                pass
    return []

async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
        print("Step 1: Getting location IDs...")
        ids = {}
        for place in PLACES:
            lid = await get_location_id(c, place)
            if lid:
                ids[place] = lid
            await asyncio.sleep(0.5)

        print(f"\nGot {len(ids)} location IDs")
        print("\nStep 2: Testing church searches...")
        all_results = []
        for label, lid in list(ids.items())[:5]:
            results = await test_search(c, lid, label)
            all_results.extend(results)
            await asyncio.sleep(2)

        print(f"\nTotal church properties found: {len(all_results)}")

asyncio.run(main())
