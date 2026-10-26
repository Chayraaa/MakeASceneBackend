"""Store recipient timezone preferences."""
from alembic import op
import sqlalchemy as sa

revision = "d84eab6109f2"
down_revision = "c28f90a61d32"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"))


def downgrade():
    op.drop_column("users", "timezone")
