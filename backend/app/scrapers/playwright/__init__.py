"""
Playwright scrapers — for JavaScript-rendered sites that httpx cannot scrape.

These require the playwright worker container to be running.
See docker-compose.playwright.yml for setup.

Sites requiring Playwright (confirmed JS-rendered):
  - Rightmove        (React, property data loaded via API)
  - Zoopla           (React, Cloudflare protected)
  - OnTheMarket      (Next.js, search results loaded client-side)
  - SDL Auctions     (React, search results via AJAX)
  - Allsop           (React, lots loaded client-side)
  - Auction House UK (WordPress with AJAX search)

Status: PENDING — Playwright worker not yet configured.
"""
