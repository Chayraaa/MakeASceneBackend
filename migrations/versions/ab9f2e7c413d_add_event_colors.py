"""Add colors to events and backfill existing events."""
from alembic import op
import sqlalchemy as sa

revision = "ab9f2e7c413d"
down_revision = "f3a71c8d902b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("events", sa.Column("colors", sa.JSON(), nullable=False, server_default='["#3366CC"]'))
    op.alter_column("events", "colors", server_default=None)


def downgrade():
    op.drop_column("events", "colors")
