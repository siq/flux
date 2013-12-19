"""add slot_order to request

Revision: 4d1fb30a5c84
Revises: 384bb0af702c
Created: 2013-12-19 12:46:56.680919
"""

revision = '4d1fb30a5c84'
down_revision = '384bb0af702c'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('request', Column('slot_order', ArrayType(TextType()), nullable=True))

def downgrade():
    op.drop_column('request', 'slot_order')
