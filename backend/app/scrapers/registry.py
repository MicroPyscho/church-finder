from app.scrapers.clive_emson              import CliveEmsonScraper
from app.scrapers.allsop                   import AllsopScraper
from app.scrapers.sdl                      import SDLScraper
from app.scrapers.uk_auction_list          import UKAuctionListScraper
from app.scrapers.eig                      import EIGScraper
from app.scrapers.auction_house            import AuctionHouseScraper
from app.scrapers.barnard_marcus           import BarnardMarcusScraper
from app.scrapers.alex_martin              import AlexMartinScraper
from app.scrapers.rightmove_chapels        import RightmoveChapelsScraper
from app.scrapers.onthemarket              import OnTheMarketScraper
from app.scrapers.jitty                    import JittyScraper
from app.scrapers.openrent                 import OpenRentScraper
from app.scrapers.church_of_england        import ChurchOfEnglandScraper
from app.scrapers.church_of_scotland       import ChurchOfScotlandScraper
from app.scrapers.church_of_wales          import ChurchOfWalesScraper
from app.scrapers.methodist                import MethodistScraper
from app.scrapers.diocese_london           import DioceseLondonScraper
from app.scrapers.churches_conservation_trust import ChurchesConservationTrustScraper
from app.scrapers.church_growth_trust      import ChurchGrowthTrustScraper
from app.scrapers.church_times             import ChurchTimesScraper
from app.scrapers.baptist_times            import BaptistTimesScraper
from app.scrapers.cofe_synod               import CoESynodScraper
from app.scrapers.charities                import CharitiesScraper
from app.scrapers.companies_house          import CompaniesHouseScraper
from app.scrapers.land_registry            import LandRegistryScraper
from app.scrapers.gov_uk                   import GovUKScraper
from app.scrapers.sw_property             import SWPropertyScraper
from app.scrapers.planning                 import PlanningSignalScraper

SCRAPERS: dict[str, type] = {
    # Specialist agents
    "alex_martin":                  AlexMartinScraper,
    # Auction houses
    "clive_emson":                  CliveEmsonScraper,
    "allsop":                       AllsopScraper,
    "sdl":                          SDLScraper,
    "uk_auction_list":              UKAuctionListScraper,
    "eig":                          EIGScraper,
    "auction_house":                AuctionHouseScraper,
    "barnard_marcus":               BarnardMarcusScraper,
    # Property portals
    "rightmove":                    RightmoveChapelsScraper,
    "onthemarket":                  OnTheMarketScraper,
    "jitty":                        JittyScraper,
    "openrent":                     OpenRentScraper,
    # Church bodies
    "church_of_england":            ChurchOfEnglandScraper,
    "church_of_scotland":           ChurchOfScotlandScraper,
    "church_of_wales":              ChurchOfWalesScraper,
    "methodist":                    MethodistScraper,
    "diocese_london":               DioceseLondonScraper,
    "churches_conservation_trust":  ChurchesConservationTrustScraper,
    "church_growth_trust":          ChurchGrowthTrustScraper,
    # Publications
    "church_times":                 ChurchTimesScraper,
    "baptist_times":                BaptistTimesScraper,
    "cofe_synod":                   CoESynodScraper,
    # Government & signals
    "charities":                    CharitiesScraper,
    "companies_house":              CompaniesHouseScraper,
    "land_registry":                LandRegistryScraper,
    "gov_uk":                       GovUKScraper,
    "sw_property":                  SWPropertyScraper,
    "planning":                     PlanningSignalScraper,
}

SOURCE_CONFIDENCE = {
    "Alex Martin Commercial":          0.99,
    "Clive Emson Auctions":            0.97,
    "Allsop Auctions":                 0.96,
    "SDL Auctions":                    0.95,
    "UK Auction List":                 0.93,
    "EIG Property Auctions":           0.93,
    "Auction House UK":                0.92,
    "Barnard Marcus Auctions":         0.91,
    "Rightmove":                       0.90,
    "OnTheMarket":                     0.90,
    "Jitty":                           0.88,
    "OpenRent":                        0.85,
    "Church of England":               0.98,
    "Church of Scotland":              0.98,
    "Church in Wales":                 0.98,
    "Methodist Church":                0.97,
    "Diocese of London":               0.96,
    "Churches Conservation Trust":     0.95,
    "Church Growth Trust":             0.94,
    "Church Times":                    0.80,
    "Baptist Times":                   0.78,
    "CoE Synod":                       0.75,
    "Charities Commission":            0.88,
    "Companies House":                 0.82,
    "HMLR Land Registry":              1.00,
    "GOV.UK":                          0.90,
    "Planning Portal":                 0.78,
}
