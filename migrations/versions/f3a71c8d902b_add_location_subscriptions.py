"""Add user subscriptions to locations."""
from alembic import op
import sqlalchemy as sa

revision = "f3a71c8d902b"
down_revision = "e2f4a67b901c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "location_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "location_id", name="uq_location_subscriptions_user_target"),
    )
    op.create_index("ix_location_subscriptions_user_id", "location_subscriptions", ["user_id"])
    op.create_index("ix_location_subscriptions_location_id", "location_subscriptions", ["location_id"])


def downgrade():
    op.drop_table("location_subscriptions")
