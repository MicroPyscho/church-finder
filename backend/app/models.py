from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id            = Column(String, primary_key=True)
    source        = Column(String, nullable=False)
    title         = Column(String, nullable=False)
    price         = Column(String, nullable=True)
    location      = Column(String, nullable=True)
    url           = Column(String, nullable=True)
    description   = Column(Text, nullable=True)
    images        = Column(Text, nullable=True)
    notified      = Column(Boolean, default=False)
    first_seen    = Column(DateTime, default=datetime.utcnow)
    last_seen     = Column(DateTime, default=datetime.utcnow)
    is_active     = Column(Boolean, default=True)
    is_off_market = Column(Boolean, default=False)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    started_at    = Column(DateTime, default=datetime.utcnow)
    finished_at   = Column(DateTime, nullable=True)
    new_listings  = Column(Integer, default=0)
    total_scraped = Column(Integer, default=0)
    errors        = Column(String, nullable=True)
    triggered_by  = Column(String, nullable=True)


class Deployment(Base):
    __tablename__ = "deployments"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    environment = Column(String, nullable=False)
    version     = Column(String, nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow)
    deployed_by = Column(String, nullable=True)
    status      = Column(String, default="active")
    notes       = Column(Text, nullable=True)
