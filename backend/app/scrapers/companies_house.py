import asyncio
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedListing

class CompaniesHouseScraper(BaseScraper):
    source_name = "Companies House"
    source_type = "httpx"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        for status in ["dissolved","liquidation"]:
            url = f"https://find-and-update.company-information.service.gov.uk/advanced-search/get-results?companyNameIncludes=church&sicCodes=94910&companyStatus={status}"
            try:
                r = await client.get(url, timeout=20, follow_redirects=True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "lxml")
                for row in soup.select("li[class*=type],div[class*=company],[class*=result]"):
                    text = row.get_text(" ",strip=True)
                    if len(text) < 10: continue
                    link = row.select_one("a[href]")
                    if not link: continue
                    href = link.get("href","")
                    if href.startswith("/"): href = "https://find-and-update.company-information.service.gov.uk" + href
                    results.append(self.make_listing(
                        url=href,
                        title=f"[COMPANY SIGNAL] {text[:100]}",
                        price_raw=f"Status: {status}", location="England",
                        description=f"Companies House SIC 94910 religious org, status={status}. {text[:300]}",
                        property_type="church", is_signal=True, signal_type="company",
                    ))
            except Exception as e:
                self.logger.warning("Companies House %s failed: %s", status, e)
            await asyncio.sleep(2)
        self.log_result(len(results))
        return results
