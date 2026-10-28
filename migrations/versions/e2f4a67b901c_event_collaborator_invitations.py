"""Give collaborator invitations IDs and a pending/accepted state."""
from alembic import op
import sqlalchemy as sa

revision = "e2f4a67b901c"
down_revision = "d84eab6109f2"
branch_labels = None
depends_on = None


def upgrade():
    # Copy into a table with a generated primary key so existing pairs get IDs.
    invitations = op.create_table(
        "event_collaborator_invitations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_account_id", sa.Integer(), sa.ForeignKey("site_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("event_id", "site_account_id", name="uq_event_collaborators_event_site"),
    )
    previous = sa.table("event_collaborators", sa.column("event_id"), sa.column("site_account_id"))
    # Existing collaborations predate the invitation workflow; preserve them as accepted.
    op.execute(invitations.insert().from_select(
        ["event_id", "site_account_id", "accepted"],
        sa.select(previous.c.event_id, previous.c.site_account_id, sa.true()),
    ))
    op.drop_table("event_collaborators")
    op.rename_table("event_collaborator_invitations", "event_collaborators")


def downgrade():
    previous = op.create_table(
        "event_collaborators_previous",
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("site_account_id", sa.Integer(), sa.ForeignKey("site_accounts.id", ondelete="CASCADE"), primary_key=True),
    )
    invitations = sa.table("event_collaborators", sa.column("event_id"), sa.column("site_account_id"))
    op.execute(previous.insert().from_select(
        ["event_id", "site_account_id"], sa.select(invitations.c.event_id, invitations.c.site_account_id),
    ))
    op.drop_table("event_collaborators")
    op.rename_table("event_collaborators_previous", "event_collaborators")
