"""Add event visibility, including existing events."""
from alembic import op
import sqlalchemy as sa

revision = "c28f90a61d32"
down_revision = "b1f84c92d7a0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("events", sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    op.drop_column("events", "visible")
