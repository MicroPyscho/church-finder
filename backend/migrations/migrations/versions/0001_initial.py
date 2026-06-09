"""Initial schema — listings, deployments, crawl_runs

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id",          sa.String(64),  nullable=False),
        sa.Column("source",      sa.String(120), nullable=False),
        sa.Column("title",       sa.String(500), nullable=False),
        sa.Column("price",       sa.String(80),  nullable=False, server_default="POA"),
        sa.Column("location",    sa.String(200), nullable=False, server_default=""),
        sa.Column("url",         sa.Text(),      nullable=False),
        sa.Column("description", sa.Text(),      nullable=False, server_default=""),
        sa.Column("notified",    sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("first_seen",  sa.DateTime(),  nullable=False),
        sa.Column("last_seen",   sa.DateTime(),  nullable=False),
        sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listings_first_seen",  "listings", ["first_seen"])
    op.create_index("ix_listings_is_active",   "listings", ["is_active"])
    op.create_index("ix_listings_source",      "listings", ["source"])

    op.create_table(
        "deployments",
        sa.Column("id",           postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("environment",  sa.String(20),  nullable=False),
        sa.Column("version",      sa.String(80),  nullable=False),
        sa.Column("image_tag",    sa.String(200), nullable=False),
        sa.Column("deployed_by",  sa.String(100), nullable=False, server_default="ci"),
        sa.Column("deployed_at",  sa.DateTime(),  nullable=False),
        sa.Column("is_current",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("rollback_of",  postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("notes",        sa.Text(),      nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deployments_environment", "deployments", ["environment"])
    op.create_index("ix_deployments_is_current",  "deployments", ["is_current"])
    op.create_index("ix_deployments_deployed_at", "deployments", ["deployed_at"])

    op.create_table(
        "crawl_runs",
        sa.Column("id",            sa.Integer(),  nullable=False, autoincrement=True),
        sa.Column("started_at",    sa.DateTime(), nullable=False),
        sa.Column("finished_at",   sa.DateTime(), nullable=True),
        sa.Column("new_listings",  sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("total_scraped", sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("errors",        sa.Text(),     nullable=False, server_default=""),
        sa.Column("triggered_by",  sa.String(40), nullable=False, server_default="scheduler"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crawl_runs_started_at", "crawl_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("crawl_runs")
    op.drop_table("deployments")
    op.drop_table("listings")
    