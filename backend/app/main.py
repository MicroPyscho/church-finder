from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.database import engine, Base
from app.logging_config import configure_logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.scheduler import start_scheduler, stop_scheduler
from app.routers import listings, deployments, health, properties, favourites, enquiry
from app.routers import search

# Configure structured logging before anything else
configure_logging()

# Rate limiter — 60 searches/min per IP (protects Groq free tier)
# Switch to Redis backend when scaling beyond single server
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler(crawl_hours=settings.CRAWL_INTERVAL_HOURS)
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="Sanctuary API",
    description="UK Church & Gathering Space Property Search",
    version=settings.APP_VERSION,
    docs_url="/docs"   if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,       prefix="/health",         tags=["health"])
app.include_router(listings.router,     prefix="/listings",       tags=["listings"])
app.include_router(deployments.router,  prefix="/deployments",    tags=["deployments"])
app.include_router(properties.router,   prefix="/api/properties", tags=["properties"])
app.include_router(favourites.router,   prefix="/api/favourites", tags=["favourites"])
app.include_router(search.router,       prefix="/api/search",     tags=["search"])
app.include_router(enquiry.router)
