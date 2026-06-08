import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing, extract_price

PROPERTY_TERMS = [
    "for sale", "to let", "available", "disposal", "redundant",
    "closed chapel", "closed church", "surplus", "sold", "under offer",
    "lease", "freehold", "leasehold", "offers invited",
]

EXCLUDE_TERMS = [
    "steward", "pension", "payroll", "salary", "living wage",
    "net zero", "carbon", "job description", "safeguarding",
    "liturgy", "prayer", "bible study", "conference", "synod",
    "circuit steward", "what is a", "called to be", "how are",
    "endings:", "leadership", "governance", "policy",
]

class MethodistScraper(BaseScraper):
    source_name = "Methodist Church"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        # Methodist property for sale page — only this specific URL
        url = "https://www.methodist.org.uk/for-churches/property/"
        try:
            r = await client.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # Only pick up items that explicitly mention property transactions
            for item in soup.select("article, div[class*=property], div[class*=listing], li[class*=property]"):
                text = item.get_text(" ", strip=True)
                text_lower = text.lower()

                # Must mention a property transaction term
                if not any(t in text_lower for t in PROPERTY_TERMS):
                    continue
                # Must not be a governance/admin article
                if any(e in text_lower for e in EXCLUDE_TERMS):
                    continue
                if len(text) < 30:
                    continue

                link = item.select_one("a[href]")
                if not link:
                    continue
                href = link.get("href", "")
                if href.startswith("/"): href = "https://www.methodist.org.uk" + href

                title_el = item.select_one("h2, h3, [class*=title]")
                title = title_el.get_text(strip=True) if title_el else text[:120]

                results.append(self.make_listing(
                    url=href, title=title,
                    price_raw=extract_price(text) or "Enquire",
                    location="England", description=text[:400],
                    property_type="church",
                ))

        except Exception as e:
            self.logger.warning("Methodist failed: %s", e)

        self.log_result(len(results))
        return results
