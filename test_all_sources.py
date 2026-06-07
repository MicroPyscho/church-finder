import asyncio
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}

SOURCES = [
    ("Rightmove commercial church", "https://www.rightmove.co.uk/commercial-property-for-sale/find.html?searchType=SALE&keywords=church"),
    ("Rightmove converted chapel", "https://www.rightmove.co.uk/property-for-sale/find.html?keywords=converted+chapel"),
    ("Zoopla church", "https://www.zoopla.co.uk/for-sale/property/uk/?q=church+chapel"),
    ("OnTheMarket former chapel", "https://www.onthemarket.com/for-sale/property/uk/?keywords=former+chapel"),
    ("Savills church", "https://www.savills.co.uk/search/?sch=buy&searchType=2&q=church"),
    ("Jitty converted church", "https://jitty.com/for-sale/england/look-for-converted_church"),
    ("OpenRent church hall", "https://www.openrent.co.uk/properties-to-rent/?term=church+hall"),
    ("LoopNet UK church", "https://www.loopnet.co.uk/search/commercial-real-estate/united-kingdom/for-sale/?sk=church"),
    ("4prop church rent", "https://www.4prop.com/commercial-property-for-rent/?q=church"),
    ("Clive Emson church", "https://www.cliveemson.co.uk/properties/?keyword=church"),
    ("Allsop residential", "https://www.allsop.co.uk/auctions/residential-auctions/"),
    ("Allsop commercial", "https://www.allsop.co.uk/auctions/commercial-auctions/"),
    ("SDL Auctions church", "https://www.sdlauctions.co.uk/property-list/?search=church"),
    ("UK Auction List church", "https://ukauctionlist.com/?s=church"),
    ("EIG Auctions church", "https://www.eigpropertyauctions.co.uk/search?q=church"),
    ("Alex Martin places of worship", "https://alexmartin.co.uk/places-of-worship/"),
    ("Alex Martin listings", "https://alexmartin.co.uk/listings/"),
    ("CoE property", "https://www.churchofengland.org/resources/property"),
    ("CoE churches for sale", "https://www.churchofengland.org/resources/property/churches-for-sale"),
    ("CoE commercial property", "https://www.churchofengland.org/resources/property/commercial-property"),
    ("Church of Scotland property", "https://www.churchofscotland.org.uk/resources/property"),
    ("Church in Wales properties", "https://www.churchinwales.org.uk/en/about-us/our-properties/"),
    ("Methodist property", "https://www.methodist.org.uk/for-churches/property/"),
    ("Methodist property for sale", "https://www.methodist.org.uk/for-churches/property/property-for-sale/"),
    ("Baptist Union property", "https://www.baptist.org.uk/Groups/220597/Property.aspx"),
    ("Baptist Union old URL", "https://www.baptist.org.uk/Articles/368986/Properties_for_Sale.aspx"),
    ("Diocese of London property", "https://www.london.anglican.org/properties/"),
    ("Diocese of London articles", "https://www.london.anglican.org/articles/category/property/"),
    ("Church Growth Trust", "https://www.cgt.org.uk/properties"),
    ("Church Times buildings", "https://www.churchtimes.co.uk/topics/church-buildings"),
    ("Baptist Times", "https://www.baptisttimes.co.uk"),
    ("Historic England HAR churches", "https://historicengland.org.uk/advice/heritage-at-risk/search-register/?term=church&type=place-of-worship"),
    ("Historic England HAR search", "https://historicengland.org.uk/listing/heritage-at-risk/search-register/"),
    ("GOV.UK surplus church", "https://www.gov.uk/search/all?keywords=surplus+church&order=updated-newest"),
    ("GOV.UK church disposal", "https://www.gov.uk/search/all?keywords=church+disposal"),
    ("Companies House religious", "https://find-and-update.company-information.service.gov.uk/advanced-search/get-results?companyNameIncludes=church&sicCodes=94910&companyStatus=dissolved"),
    ("Charities Commission", "https://register-of-charities.charitycommission.gov.uk/charity-search?q=church&status=RM&subCategory=202"),
    ("HMLR Price Paid API", "https://landregistry.data.gov.uk/data/ppi/transaction-record.json?propertyType=O&_pageSize=10"),
    ("Deal Connect commercial", "https://www.dealconnect.co.uk/deals?type=commercial"),
    ("CoE Synod papers", "https://www.churchofengland.org/about/general-synod/papers-and-reports"),
    ("Methodist Conference agendas", "https://www.methodist.org.uk/about/conference/agendas/"),
    ("Baptist Assembly", "https://www.baptist.org.uk/Groups/220595/Assembly.aspx"),
]

async def test_url(client, name, url):
    try:
        r = await client.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        status = r.status_code
        ct = r.headers.get("content-type", "")
        if status == 200:
            if "json" in ct:
                try:
                    data = r.json()
                    count = len(data) if isinstance(data, list) else sum(len(v) for v in data.values() if isinstance(v, list))
                    return (name, "OK_JSON", f"{count} items", url)
                except:
                    return (name, "OK_JSON", "parse error", url)
            else:
                soup = BeautifulSoup(r.text, "lxml")
                title = soup.find("title")
                t = title.text.strip()[:55] if title else "no title"
                links = len(soup.find_all("a", href=True))
                church = any(kw in r.text.lower() for kw in ["church","chapel","property","listing","lot","auction"])
                return (name, "OK_HTML", f"'{t}' | {links} links | church={church}", url)
        elif status in (301, 302):
            return (name, f"REDIRECT_{status}", r.headers.get("location","?")[:60], url)
        elif status == 403:
            return (name, "BLOCKED_403", "bot protection", url)
        elif status == 404:
            return (name, "DEAD_404", "page not found", url)
        elif status == 429:
            return (name, "RATELIMITED_429", "slow down", url)
        else:
            return (name, f"STATUS_{status}", "", url)
    except asyncio.TimeoutError:
        return (name, "TIMEOUT", "no response in 15s", url)
    except Exception as e:
        return (name, "ERROR", str(e)[:60], url)

async def main():
    results = []
    async with httpx.AsyncClient(follow_redirects=False, timeout=15) as client:
        for i in range(0, len(SOURCES), 4):
            batch = SOURCES[i:i+4]
            br = await asyncio.gather(*[test_url(client, n, u) for n, u in batch])
            results.extend(br)
            await asyncio.sleep(1)

    cats = {"WORKING": [], "BLOCKED": [], "DEAD": [], "OTHER": []}
    for r in results:
        if r[1].startswith("OK"):          cats["WORKING"].append(r)
        elif "403" in r[1] or "429" in r[1]: cats["BLOCKED"].append(r)
        elif "404" in r[1] or "ERROR" in r[1] or "TIMEOUT" in r[1]: cats["DEAD"].append(r)
        else:                               cats["OTHER"].append(r)

    print("=" * 70)
    print("SANCTUARY SOURCE TEST REPORT")
    print("=" * 70)
    for cat, items in cats.items():
        print(f"\n--- {cat} ({len(items)}) ---")
        for name, status, detail, url in items:
            print(f"  [{status}] {name}")
            print(f"           {detail}")
            print(f"           {url}")
    print("\n" + "=" * 70)
    print(f"TOTAL: {len(cats['WORKING'])} working | {len(cats['BLOCKED'])} blocked | {len(cats['DEAD'])} dead | {len(cats['OTHER'])} other")

asyncio.run(main())
