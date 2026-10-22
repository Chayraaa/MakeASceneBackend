"""Add optional site-account profile pictures.

Revision ID: b6d9f310a2c8
Revises: a4e8c29d106f
"""
from alembic import op
import sqlalchemy as sa

revision = "b6d9f310a2c8"
down_revision = "a4e8c29d106f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("site_accounts", sa.Column("profile_picture", sa.String(), nullable=True))


def downgrade():
    op.drop_column("site_accounts", "profile_picture")
