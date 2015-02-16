"""add_run_environment

Revision: 494215ec15e4
Revises: 3e89ba0f54a1
Created: 2015-02-16 11:02:45.007782
"""

revision = '494215ec15e4'
down_revision = '3e89ba0f54a1'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('run', Column('environment', JsonType(), nullable=True))

def downgrade():
    op.drop_column('run', 'environment')
