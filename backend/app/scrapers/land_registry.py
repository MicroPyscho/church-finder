import asyncio
from app.scrapers.base import BaseScraper, ScrapedListing

class LandRegistryScraper(BaseScraper):
    source_name = "HMLR Land Registry"
    source_type = "api"

    async def scrape(self, client) -> list[ScrapedListing]:
        results = []
        url = "https://landregistry.data.gov.uk/data/ppi/transaction-record.json?propertyType=O&_pageSize=50&_sort=-transactionDate"
        try:
            r = await client.get(url, timeout=15, follow_redirects=True)
            r.raise_for_status()
            data = r.json()
            for tx in data.get("result",{}).get("items",[]):
                addr = tx.get("propertyAddress",{})
                title_str = f"{addr.get('paon','')} {addr.get('street','')} {addr.get('town','')}".strip()
                price = tx.get("pricePaid",0)
                tx_id = tx.get("transactionId", title_str)
                prop_url = f"https://landregistry.data.gov.uk/data/ppi/transaction-record/{tx_id}"
                results.append(self.make_listing(
                    url=prop_url,
                    title=f"[HMLR] Commercial transaction: {title_str}",
                    price_raw=f"£{price:,}" if price else "Unknown",
                    location=addr.get("town","England"),
                    description=f"Land Registry commercial transaction. Postcode: {addr.get('postcode','')}.",
                    property_type="other", is_signal=True, signal_type="land_registry",
                ))
        except Exception as e:
            self.logger.warning("HMLR failed: %s", e)
        self.log_result(len(results))
        return results
