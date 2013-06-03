"""add_products

Revision: 3bf7984d0e85
Revises: 26a9262ee8f9
Created: 2013-06-02 19:18:00.796234
"""

revision = '3bf7984d0e85'
down_revision = '26a9262ee8f9'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('run', Column('products', JsonType(), nullable=True))

def downgrade():
    op.drop_column('run', 'products')
