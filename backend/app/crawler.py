import asyncio, hashlib, logging, re
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Listing, CrawlRun

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}

CORE_KEYWORDS = [
    "church","chapel","ecclesiastical","vestry","nave","place of worship",
    "religious building","tabernacle","congregation","parish","minster",
    "priory","abbey","meeting house","mission hall","redundant church",
    "former church","methodist","baptist","anglican","quaker",
    "salvation army","kingdom hall","village hall","community hall",
    "assembly hall","masonic hall","memorial hall","working men's club",
    "social club","drill hall","civic hall","parish hall","function hall",
    "banqueting hall","institute building","warehouse conversion",
    "mill building","barn conversion","former theatre","former cinema",
    "bingo hall","former school","leisure centre","change of use",
    "d1","f1 use class","listed building","surplus property","disposal",
    "graveyard","churchyard","high ceiling","clear span","auditorium",
]

RIGHTMOVE_REGIONS = [
    ("Kent","REGION%5E61"),("East Sussex","REGION%5E45"),
    ("West Sussex","REGION%5E46"),("Surrey","REGION%5E91"),
    ("Hampshire","REGION%5E54"),("Oxfordshire","REGION%5E74"),
    ("Essex","REGION%5E47"),("Suffolk","REGION%5E90"),
    ("Yorkshire","REGION%5E103"),("Lancashire","REGION%5E62"),
]

OTM_REGIONS = [
    "kent","east-sussex","surrey","hampshire","oxfordshire",
    "essex","suffolk","yorkshire","lancashire","gloucestershire",
]

def make_id(source, url): return hashlib.md5(f"{source}:{url}".encode()).hexdigest()
def has_keyword(text): t=text.lower(); return any(k in t for k in CORE_KEYWORDS)
def parse_price(text): return text.strip().replace("\n"," ")[:80]
def classify(text):
    t=text.lower()
    if any(k in t for k in ["church","chapel","ecclesiastical","vestry","tabernacle","place of worship"]): return "church"
    if any(k in t for k in ["village hall","community hall","masonic","memorial hall","drill hall","parish hall","working men's club"]): return "hall"
    if any(k in t for k in ["warehouse","mill","theatre","cinema","bingo hall","former school","leisure centre","barn"]): return "large_space"
    return "other"

async def fetch(client, url):
    try:
        r = await client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as exc:
        logger.warning("Fetch failed %s: %s", url, exc)
        return None

async def scrape_rightmove(client):
    results=[]; seen=set()
    for label,region_id in RIGHTMOVE_REGIONS:
        url=f"https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier={region_id}&keywords=church&sortType=6&includeSSTC=false"
        soup=await fetch(client,url)
        if not soup: continue
        for card in soup.select("div.l-searchResult"):
            link_el=card.select_one("a.propertyCard-link")
            if not link_el: continue
            href="https://www.rightmove.co.uk"+link_el.get("href","")
            if href in seen: continue
            seen.add(href)
            title=(card.select_one("h2.propertyCard-title") or card).get_text(strip=True)[:300]
            desc_el=card.select_one("div.propertyCard-description")
            desc=desc_el.get_text(strip=True) if desc_el else ""
            if not has_keyword(f"{title} {desc}"): continue
            price_el=card.select_one("div.propertyCard-priceValue")
            addr_el=card.select_one("address.propertyCard-address")
            results.append({"id":make_id("rightmove",href),"source":"Rightmove","title":title,"price":parse_price(price_el.get_text() if price_el else "POA"),"location":addr_el.get_text(strip=True) if addr_el else label,"url":href,"description":desc,"property_type":classify(f"{title} {desc}")})
        await asyncio.sleep(2)
    return results

async def scrape_onthemarket(client):
    results=[]; seen=set()
    for region in OTM_REGIONS:
        url=f"https://www.onthemarket.com/for-sale/property/{region}/?keywords=church"
        soup=await fetch(client,url)
        if not soup: continue
        for card in soup.select("li.otm-PropertyCardInfo,div.property-card"):
            link_el=card.select_one("a[href]")
            if not link_el: continue
            href=link_el.get("href","")
            if not href.startswith("http"): href="https://www.onthemarket.com"+href
            if href in seen: continue
            seen.add(href)
            text=card.get_text(" ",strip=True)
            if not has_keyword(text): continue
            title_el=card.select_one("h2,h3,.title")
            price_el=card.select_one(".price,.property-price")
            addr_el=card.select_one(".address,.location")
            results.append({"id":make_id("otm",href),"source":"OnTheMarket","title":title_el.get_text(strip=True) if title_el else text[:120],"price":parse_price(price_el.get_text() if price_el else "POA"),"location":addr_el.get_text(strip=True) if addr_el else region,"url":href,"description":text[:400],"property_type":classify(text)})
        await asyncio.sleep(2)
    return results

async def scrape_clive_emson(client):
    # Clive Emson stores price and location in data-attributes on the card div
    # e.g. data-price="£150,000" data-loc="Thanet Area - Kent Area"
    results=[]; seen=set()
    for term in ["church","chapel","hall","former+school","community+hall"]:
        url=f"https://www.cliveemson.co.uk/properties/?keyword={term}"
        soup=await fetch(client,url)
        if not soup: continue
        cards=soup.select("div.lot")
        logger.info("Clive Emson '%s': %d cards",term,len(cards))
        for card in cards:
            # Pull from data attributes - this is where real data lives
            title = card.get("data-cathead","").strip()
            price = card.get("data-price","").strip()
            if not price:
                # Price is sometimes in the description text
                import re
                desc_text = card.get_text(" ", strip=True)
                price_match = re.search(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?', desc_text)
                price = price_match.group(0) if price_match else "Nil Reserve"
            location = card.get("data-loc","South East").strip()
            lot_num = card.get("data-lot","")
            auction = card.get("data-auc","")

            if not title:
                title_el = card.select_one("h2,h3,.lot-title,.property-title")
                title = title_el.get_text(strip=True) if title_el else ""

            if not has_keyword(title): continue

            # Build URL from auction and lot number
            if auction and lot_num:
                href = f"https://www.cliveemson.co.uk/properties/{auction}/lot-{lot_num}/"
            else:
                link_el = card.select_one("a[href]")
                href = link_el.get("href","") if link_el else ""
                if href.startswith("/"): href="https://www.cliveemson.co.uk"+href

            if not href or href in seen: continue
            seen.add(href)

            text = card.get_text(" ",strip=True)
            results.append({
                "id":make_id("clive_emson",href),
                "source":"Clive Emson Auctions",
                "title":title,
                "price":price,
                "location":location,
                "url":href,
                "description":text[:400],
                "property_type":classify(title),
            })
        await asyncio.sleep(2)
    return results

async def scrape_allsop(client):
    results=[]
    url="https://www.allsop.co.uk/auctions/residential/"
    soup=await fetch(client,url)
    if not soup: return results
    for lot in soup.select("div.lot,article.lot,div.property-result,li.lot"):
        text=lot.get_text(" ",strip=True)
        if not has_keyword(text): continue
        link_el=lot.select_one("a[href]")
        if not link_el: continue
        href=link_el.get("href",url)
        if href.startswith("/"): href="https://www.allsop.co.uk"+href
        title_el=lot.select_one("h2,h3,.lot-title")
        price_el=lot.select_one(".guide,.guide-price,.price")
        addr_el=lot.select_one(".address,.location")
        results.append({"id":make_id("allsop",href),"source":"Allsop Auctions","title":title_el.get_text(strip=True) if title_el else text[:120],"price":parse_price(price_el.get_text() if price_el else "TBC"),"location":addr_el.get_text(strip=True) if addr_el else "England","url":href,"description":text[:400],"property_type":classify(text)})
    return results

async def scrape_church_of_england(client):
    results=[]
    for url in ["https://www.churchofengland.org/resources/property/churches-for-sale","https://www.churchofengland.org/resources/property"]:
        soup=await fetch(client,url)
        if not soup: continue
        for item in soup.select("div.property-listing,article,div.views-row,li.property"):
            text=item.get_text(" ",strip=True)
            if not has_keyword(text): continue
            link_el=item.select_one("a[href]")
            if not link_el: continue
            href=link_el.get("href","")
            if href.startswith("/"): href="https://www.churchofengland.org"+href
            title_el=item.select_one("h2,h3,.title")
            results.append({"id":make_id("cofe",href),"source":"Church of England","title":title_el.get_text(strip=True) if title_el else text[:120],"price":"Enquire","location":"England","url":href,"description":text[:400],"property_type":"church"})
        await asyncio.sleep(2)
    return results

def deduplicate(listings):
    seen={}
    confidence={"Church of England":0.98,"Methodist Church":0.96,"Baptist Union":0.96,"Heritage at Risk Register":0.99,"Rightmove":0.95,"OnTheMarket":0.92,"Clive Emson Auctions":0.93,"Allsop Auctions":0.93}
    for l in listings:
        key=hashlib.md5(f"{l['title'][:30].lower()}|{l['location'][:20].lower()}".encode()).hexdigest()
        if key not in seen or confidence.get(l["source"],0.5)>confidence.get(seen[key]["source"],0.5):
            seen[key]=l
    return list(seen.values())

ALL_SCRAPERS=[
    ("rightmove",scrape_rightmove),
    ("onthemarket",scrape_onthemarket),
    ("clive_emson",scrape_clive_emson),
    ("allsop",scrape_allsop),
    ("church_of_england",scrape_church_of_england),
]

async def run_crawl(db: AsyncSession, triggered_by:str="scheduler", source:str="all") -> CrawlRun:
    run=CrawlRun(started_at=datetime.utcnow(),triggered_by=triggered_by)
    db.add(run); await db.flush()
    errors=[]; total=0; new_count=0; all_listings=[]
    scrapers=ALL_SCRAPERS if source=="all" else [(n,f) for n,f in ALL_SCRAPERS if n==source]
    async with httpx.AsyncClient() as client:
        for name,fn in scrapers:
            try:
                logger.info("Scraping: %s",name)
                found=await fn(client)
                logger.info("%s: %d found",name,len(found))
                all_listings.extend(found); total+=len(found)
            except Exception as exc:
                msg=f"{name}: {exc}"; logger.error(msg); errors.append(msg)
    deduped=deduplicate(all_listings)
    logger.info("Deduped: %d unique",len(deduped))
    for data in deduped:
        try:
            existing=await db.get(Listing,data["id"])
            if existing:
                existing.last_seen=datetime.utcnow(); existing.is_active=True
                if existing.price!=data.get("price",""): existing.price=data["price"]
            else:
                db.add(Listing(id=data["id"],source=data["source"],title=data["title"],price=data["price"],location=data["location"],url=data["url"],description=data.get("description","")))
                new_count+=1
        except Exception as exc:
            errors.append(f"DB {data.get('id','?')}: {exc}")
    run.finished_at=datetime.utcnow(); run.new_listings=new_count; run.total_scraped=total; run.errors="\n".join(errors[:20])
    await db.commit()
    logger.info("Done: %d new / %d total",new_count,total)
    return run
