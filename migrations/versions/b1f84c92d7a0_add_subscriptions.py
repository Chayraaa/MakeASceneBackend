"""Add user subscriptions to events and site accounts."""
from alembic import op
import sqlalchemy as sa

revision = "b1f84c92d7a0"
down_revision = "4f3653bb63df"
branch_labels = None
depends_on = None


def upgrade():
    for kind, target in [("event", "events"), ("site_account", "site_accounts")]:
        table = f"{kind}_subscriptions"
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column(f"{kind}_id", sa.Integer(), sa.ForeignKey(f"{target}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.UniqueConstraint("user_id", f"{kind}_id", name=f"uq_{table}_user_target"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.create_index(f"ix_{table}_{kind}_id", table, [f"{kind}_id"])


def downgrade():
    for kind in ["site_account", "event"]:
        op.drop_table(f"{kind}_subscriptions")
