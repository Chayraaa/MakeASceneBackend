"""Add site-account banners, colors, contacts, descriptions and visibility."""
from alembic import op
import sqlalchemy as sa

revision = "c7e2a94b106d"
down_revision = "b6d9f310a2c8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("site_accounts", sa.Column("banner", sa.String(), nullable=False, server_default=""))
    op.add_column("site_accounts", sa.Column("colors", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("site_accounts", sa.Column("contact", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("site_accounts", sa.Column("description", sa.String(), nullable=False, server_default=""))
    op.add_column("site_accounts", sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()))
    for column in ("banner", "colors", "contact", "description", "visible"):
        op.alter_column("site_accounts", column, server_default=None)


def downgrade():
    for column in ("visible", "description", "contact", "colors", "banner"):
        op.drop_column("site_accounts", column)
