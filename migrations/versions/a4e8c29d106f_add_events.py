"""Add events and their tag and collaborator relationships.

Revision ID: a4e8c29d106f
Revises: 79f4e905a5bd
"""
from alembic import op
import sqlalchemy as sa


revision = "a4e8c29d106f"
down_revision = "79f4e905a5bd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("till", sa.DateTime(timezone=True), nullable=False),
        sa.Column("place_id", sa.String(), sa.ForeignKey("locations.place_id"), nullable=False),
        sa.Column("layout", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("site_accounts.id"), nullable=False),
        sa.Column("access", sa.JSON(), nullable=False),
        sa.Column("repeating", sa.String(), nullable=True),
        sa.Column("detail_data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "event_tags",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "event_collaborators",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("site_account_id", sa.Integer(), sa.ForeignKey("site_accounts.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade():
    op.drop_table("event_collaborators")
    op.drop_table("event_tags")
    op.drop_table("events")
