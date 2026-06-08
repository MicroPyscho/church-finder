"""
Scraper registry — single source of truth for all scrapers.

Structure:
  scrapers/httpx/       — static HTML scrapers (httpx + BeautifulSoup)
  scrapers/playwright/  — JS-rendered scrapers (require Playwright worker)

SCRAPERS dict: name -> class, for all active httpx scrapers.
PLAYWRIGHT_SCRAPERS dict: name -> class, for future Playwright scrapers.
SOURCE_CONFIDENCE: float 0-1 indicating how reliable each source is.
"""

# ── httpx scrapers (active) ────────────────────────────────────────────────

from app.scrapers.httpx.alex_martin              import AlexMartinScraper
from app.scrapers.httpx.clive_emson              import CliveEmsonScraper
from app.scrapers.httpx.allsop                   import AllsopScraper
from app.scrapers.httpx.sdl                      import SDLScraper
from app.scrapers.httpx.auction_house            import AuctionHouseScraper
from app.scrapers.httpx.barnard_marcus           import BarnardMarcusScraper
from app.scrapers.httpx.pugh_auctions            import PughAuctionsScraper
from app.scrapers.httpx.paul_fosh                import PaulFoshScraper
from app.scrapers.httpx.bidx1                    import BidX1Scraper
from app.scrapers.httpx.savills_ecclesiastical   import SavillsEcclesiasticalScraper
from app.scrapers.httpx.fisher_german            import FisherGermanScraper
from app.scrapers.httpx.sw_property              import SWPropertyScraper
from app.scrapers.httpx.onthemarket              import OnTheMarketScraper
from app.scrapers.httpx.rightmove_chapels        import RightmoveChapelsScraper
from app.scrapers.httpx.openrent                 import OpenRentScraper
from app.scrapers.httpx.jitty                    import JittyScraper
from app.scrapers.httpx.church_of_england        import ChurchOfEnglandScraper
from app.scrapers.httpx.church_of_scotland       import ChurchOfScotlandScraper
from app.scrapers.httpx.church_of_wales          import ChurchOfWalesScraper
from app.scrapers.httpx.methodist                import MethodistScraper
from app.scrapers.httpx.diocese_london           import DioceseLondonScraper
from app.scrapers.httpx.churches_conservation_trust import ChurchesConservationTrustScraper
from app.scrapers.httpx.church_growth_trust      import ChurchGrowthTrustScraper
from app.scrapers.httpx.church_times             import ChurchTimesScraper
from app.scrapers.httpx.baptist_times            import BaptistTimesScraper
from app.scrapers.httpx.cofe_synod               import CoESynodScraper
from app.scrapers.httpx.charities                import CharitiesScraper
from app.scrapers.httpx.companies_house          import CompaniesHouseScraper
from app.scrapers.httpx.land_registry            import LandRegistryScraper
from app.scrapers.httpx.gov_uk                   import GovUKScraper
from app.scrapers.httpx.planning                 import PlanningSignalScraper

from app.scrapers.playwright.btg_eddisons import BTGEddisonsScraper
from app.scrapers.playwright.rightmove import RightmoveScraper as RightmovePlaywrightScraper
from app.scrapers.playwright.onthemarket_full import OnTheMarketFullScraper

# ── Active scrapers dict ───────────────────────────────────────────────────

SCRAPERS: dict[str, type] = {

    # ── Specialist ecclesiastical agents ──
    "alex_martin":                  AlexMartinScraper,
    "sw_property":                  SWPropertyScraper,
    "savills":                      SavillsEcclesiasticalScraper,
    "fisher_german":                FisherGermanScraper,

    # ── Auction houses ──
    "clive_emson":                  CliveEmsonScraper,
    "allsop":                       AllsopScraper,
    "sdl":                          SDLScraper,
    "auction_house":                AuctionHouseScraper,
    "barnard_marcus":               BarnardMarcusScraper,
    "pugh_auctions":                PughAuctionsScraper,
    "btg_eddisons":                BTGEddisonsScraper,
    "paul_fosh":                    PaulFoshScraper,
    "bidx1":                        BidX1Scraper,

    # ── Property portals ──
    "onthemarket":                  OnTheMarketScraper,
    "onthemarket_full":             OnTheMarketFullScraper,
    "rightmove":                    RightmoveChapelsScraper,
    "rightmove_playwright":          RightmovePlaywrightScraper,
    "openrent":                     OpenRentScraper,
    "jitty":                        JittyScraper,

    # ── Church bodies ──
    "church_of_england":            ChurchOfEnglandScraper,
    "church_of_scotland":           ChurchOfScotlandScraper,
    "church_of_wales":              ChurchOfWalesScraper,
    "methodist":                    MethodistScraper,
    "diocese_london":               DioceseLondonScraper,
    "churches_conservation_trust":  ChurchesConservationTrustScraper,
    "church_growth_trust":          ChurchGrowthTrustScraper,

    # ── Publications ──
    "church_times":                 ChurchTimesScraper,
    "baptist_times":                BaptistTimesScraper,
    "cofe_synod":                   CoESynodScraper,

    # ── Government and financial signals ──
    "charities":                    CharitiesScraper,
    "companies_house":              CompaniesHouseScraper,
    "land_registry":                LandRegistryScraper,
    "gov_uk":                       GovUKScraper,
    "planning":                     PlanningSignalScraper,
}

# ── Playwright scrapers (pending worker setup) ─────────────────────────────
# These are stubbed in scrapers/playwright/ and will be activated once
# the Playwright worker container is configured.

PLAYWRIGHT_SCRAPERS: dict[str, str] = {
    "rightmove_full":       "app.scrapers.playwright.rightmove",
    "zoopla":               "app.scrapers.playwright.zoopla",
    "onthemarket_full":     "app.scrapers.playwright.onthemarket_full",
    "sdl_full":             "app.scrapers.playwright.sdl_auctions",
}

# ── Source confidence scores ───────────────────────────────────────────────
# How reliable is each source for genuine church property listings?
# 1.0 = always real church properties
# 0.7 = usually real, some false positives possible

SOURCE_CONFIDENCE: dict[str, float] = {
    "Alex Martin Commercial":       0.99,
    "SW Property":                  0.98,
    "Savills":                      0.97,
    "Fisher German":                0.95,
    "Clive Emson Auctions":         0.97,
    "Allsop Auctions":              0.96,
    "SDL Auctions":                 0.95,
    "Auction House UK":             0.92,
    "Barnard Marcus Auctions":      0.85,
    "Pugh Auctions":                0.93,
    "Paul Fosh Auctions":           0.93,
    "BidX1 Auctions":               0.90,
    "Rightmove":                    0.88,
    "OnTheMarket":                  0.88,
    "OpenRent":                     0.82,
    "Jitty":                        0.85,
    "Church of England":            0.98,
    "Church of Scotland":           0.98,
    "Church in Wales":              0.98,
    "Methodist Church":             0.97,
    "Diocese of London":            0.96,
    "Churches Conservation Trust":  0.95,
    "Church Growth Trust":          0.94,
    "Church Times":                 0.80,
    "Baptist Times":                0.78,
    "CoE Synod":                    0.75,
    "Charities Commission":         0.88,
    "Companies House":              0.82,
    "HMLR Land Registry":           1.00,
    "GOV.UK":                       0.90,
    "Planning Portal":              0.78,
}
