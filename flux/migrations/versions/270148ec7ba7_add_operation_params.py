"""add_operation_parameters

Revision: 270148ec7ba7
Revises: None
Created: 2013-03-12 19:16:32.638540
"""

revision = '270148ec7ba7'
down_revision = None

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('operation', Column('parameters', JsonType(), nullable=True))

def downgrade():
    op.drop_column('operation', 'parameters')
