import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id:          Mapped[str]  = mapped_column(String(64), primary_key=True)
    source:      Mapped[str]  = mapped_column(String(120))
    title:       Mapped[str]  = mapped_column(String(500))
    price:       Mapped[str]  = mapped_column(String(80),  default="POA")
    location:    Mapped[str]  = mapped_column(String(200), default="")
    url:         Mapped[str]  = mapped_column(Text)
    description: Mapped[str]  = mapped_column(Text, default="")
    notified:    Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                  onupdate=datetime.utcnow)
    is_active:   Mapped[bool] = mapped_column(Boolean, default=True)


class Deployment(Base):
    __tablename__ = "deployments"

    id:            Mapped[str]  = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    environment:   Mapped[str]  = mapped_column(String(20))
    version:       Mapped[str]  = mapped_column(String(80))
    image_tag:     Mapped[str]  = mapped_column(String(200))
    deployed_by:   Mapped[str]  = mapped_column(String(100), default="ci")
    deployed_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_current:    Mapped[bool] = mapped_column(Boolean, default=True)
    rollback_of:   Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True, default=None
    )
    notes:         Mapped[str]  = mapped_column(Text, default="")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id:            Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    new_listings:  Mapped[int]  = mapped_column(Integer, default=0)
    total_scraped: Mapped[int]  = mapped_column(Integer, default=0)
    errors:        Mapped[str]  = mapped_column(Text, default="")
    triggered_by:  Mapped[str]  = mapped_column(String(40), default="scheduler")
    