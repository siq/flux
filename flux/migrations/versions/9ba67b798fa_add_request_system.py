"""add_request_system

Revision: 9ba67b798fa
Revises: 31b92bf6506d
Created: 2013-07-23 02:49:09.342814
"""

revision = '9ba67b798fa'
down_revision = '31b92bf6506d'

from alembic import op
from spire.schema.fields import *
from spire.mesh import SurrogateType
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('request',
        Column('id', UUIDType(), nullable=False),
        Column('name', TextType(), nullable=False),
        Column('status', EnumerationType(), nullable=False),
        Column('originator', TokenType(), nullable=False),
        Column('assignee', TokenType(), nullable=False),
        PrimaryKeyConstraint('id'),
        UniqueConstraint('name'),
    )
    op.create_table('request_slot',
        Column('id', UUIDType(), nullable=False),
        Column('request_id', UUIDType(), nullable=False),
        Column('token', TokenType(), nullable=False),
        Column('title', TextType(), nullable=True),
        Column('slot', TokenType(), nullable=False),
        ForeignKeyConstraint(['request_id'], ['request.id'], ondelete='CASCADE'),
        PrimaryKeyConstraint('id'),
        UniqueConstraint('request_id','token'),
    )
    op.create_table('request_attachment',
        Column('id', UUIDType(), nullable=False),
        Column('request_id', UUIDType(), nullable=False),
        Column('token', TokenType(), nullable=True),
        Column('title', TextType(), nullable=True),
        Column('attachment', SurrogateType(), nullable=False),
        ForeignKeyConstraint(['request_id'], ['request.id'], ondelete='CASCADE'),
        PrimaryKeyConstraint('id'),
    )
    op.create_table('request_product',
        Column('id', UUIDType(), nullable=False),
        Column('request_id', UUIDType(), nullable=False),
        Column('token', TokenType(), nullable=False),
        Column('title', TextType(), nullable=True),
        Column('product', SurrogateType(), nullable=False),
        ForeignKeyConstraint(['request_id'], ['request.id'], ondelete='CASCADE'),
        PrimaryKeyConstraint('id'),
        UniqueConstraint('request_id','token'),
    )
    op.create_table('message',
        Column('id', UUIDType(), nullable=False),
        Column('request_id', UUIDType(), nullable=False),
        Column('author', TokenType(), nullable=False),
        Column('occurrence', DateTimeType(timezone=True), nullable=False),
        Column('message', TextType(), nullable=True),
        ForeignKeyConstraint(['request_id'], ['request.id'], ondelete='CASCADE'),
        PrimaryKeyConstraint('id'),
    )

def downgrade():
    op.drop_table('message')
    op.drop_table('request_product')
    op.drop_table('request_attachment')
    op.drop_table('request_slot')
    op.drop_table('request')
