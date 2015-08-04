"""request_creator

Revision: 1db450163e76
Revises: 35b2e281e53c
Created: 2015-08-04 15:20:19.999606
"""

revision = '1db450163e76'
down_revision = '35b2e281e53c'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('request', Column('creator', TextType(), nullable=True))

def downgrade():
    op.drop_column('request', 'creator')
