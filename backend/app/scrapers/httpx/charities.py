import asyncio, re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing

class CharitiesScraper(BaseScraper):
    source_name = "Charities Commission"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        url = "https://register-of-charities.charitycommission.gov.uk/charity-search?q=church&status=RM&subCategory=202"
        try:
            r = await client.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("div[class*=charity],tr[class*=charity],li[class*=result],[class*=search-result]"):
                text = item.get_text(" ",strip=True)
                if len(text) < 10: continue
                link = item.select_one("a[href]")
                if not link: continue
                href = link.get("href","")
                if href.startswith("/"): href = "https://register-of-charities.charitycommission.gov.uk" + href
                num = re.search(r'\b\d{6,8}\b', text)
                charity_num = num.group(0) if num else "unknown"
                t = text.lower()
                signals = []
                if "dissolution" in t or "dissolved" in t: signals.append("dissolution")
                if "late accounts" in t or "overdue" in t: signals.append("late accounts")
                if "mortgage" in t: signals.append("mortgage charge")
                if "struck off" in t: signals.append("striking-off")
                if "dormant" in t: signals.append("dormant")
                if not signals: signals = ["financial signal"]
                results.append(self.make_listing(
                    url=href,
                    title=f"[DISTRESS SIGNAL] Charity {charity_num}: {', '.join(signals)}",
                    price_raw="Pre-market signal", location="England",
                    description=f"Charity Commission: {', '.join(signals)}. Number: {charity_num}. May dispose of property soon.",
                    property_type="church", is_signal=True, signal_type="charity",
                ))
        except Exception as e:
            self.logger.warning("Charities Commission failed: %s", e)
        self.log_result(len(results))
        return results
