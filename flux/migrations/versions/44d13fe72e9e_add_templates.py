"""add_templates

Revision: 44d13fe72e9e
Revises: 1d949e7fe5a1
Created: 2013-07-27 15:56:11.011409
"""

revision = '44d13fe72e9e'
down_revision = '1d949e7fe5a1'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('emailtemplate',
        Column('id', UUIDType(), nullable=False),
        Column('template', TextType(), nullable=False),
        PrimaryKeyConstraint('id'),
        UniqueConstraint('template')
    )
    op.add_column('request', Column('template_id', UUIDType(), nullable=True))

def downgrade():
    op.drop_column('request', 'template_id')
    op.drop_table('emailtemplate')
