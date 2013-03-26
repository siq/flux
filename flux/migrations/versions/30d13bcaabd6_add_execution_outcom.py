"""add_execution_outcome

Revision: 30d13bcaabd6
Revises: 83ac97de615
Created: 2013-03-25 22:23:01.288851
"""

revision = '30d13bcaabd6'
down_revision = '83ac97de615'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('execution', Column('outcome', TokenType(), nullable=True))

def downgrade():
    op.drop_column('execution', 'outcome')
