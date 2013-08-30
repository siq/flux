"""remove_request_unique_name_constraint

Revision: 4c7f56b0461f
Revises: 2a7c3bf7b40
Created: 2013-08-30 09:40:39.076509
"""

revision = '4c7f56b0461f'
down_revision = '2a7c3bf7b40'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.drop_constraint('request_name_key', 'request')

def downgrade():
    pass
