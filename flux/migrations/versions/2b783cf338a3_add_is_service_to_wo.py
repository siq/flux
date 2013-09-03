"""add is_service to workflow

Revision: 2b783cf338a3
Revises: 4c7f56b0461f
Created: 2013-09-03 14:43:25.349836
"""

revision = '2b783cf338a3'
down_revision = '4c7f56b0461f'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('workflow', Column('is_service', BooleanType(), nullable=True))
    op.execute('update workflow set is_service = false')
    op.alter_column('workflow', 'is_service', nullable=False)

def downgrade():
    op.drop_column('workflow', 'is_service')
