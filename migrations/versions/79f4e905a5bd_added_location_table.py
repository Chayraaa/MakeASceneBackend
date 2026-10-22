"""Added location table

Revision ID: 79f4e905a5bd
Revises: f957e18bb581
Create Date: 2026-10-06 22:56:48.422425

"""
import geoalchemy2
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79f4e905a5bd'
down_revision = 'f957e18bb581'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('place_id', sa.String(), nullable=False),
        sa.Column('details', sa.String(), nullable=False),
        sa.Column(
            'geometry',
            geoalchemy2.types.Geometry(
                srid=4326,
                dimension=2,
                from_text='ST_GeomFromEWKT',
                name='geometry',
            ),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('place_id'),
    )

def downgrade():
    op.drop_index(
        'idx_locations_geometry',
        table_name='locations',
        postgresql_using='gist',
    )

    op.drop_table('locations')
