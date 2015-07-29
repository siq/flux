"""add_timestamps_for_claimed_completed

Revision: 35b2e281e53c
Revises: 494215ec15e4
Created: 2015-07-29 19:04:28.850799
"""

revision = '35b2e281e53c'
down_revision = '494215ec15e4'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('request', Column('claimed', DateTimeType(timezone=True), nullable=True))
    op.add_column('request', Column('completed', DateTimeType(timezone=True), nullable=True))

def downgrade():
    op.drop_column('request', 'completed')
    op.drop_column('request', 'claimed')
