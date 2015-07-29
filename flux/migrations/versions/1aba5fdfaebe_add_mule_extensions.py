"""add_mule_extensions

Revision: 1aba5fdfaebe
Revises: 494215ec15e4
Created: 2015-07-28 08:51:03.659308
"""

revision = '1aba5fdfaebe'
down_revision = '494215ec15e4'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('workflow_mule',
    Column('id', UUIDType(), nullable=False),
    Column('workflow_id', UUIDType(), nullable=False),
    Column('package', TextType(), nullable=False),
    Column('endpointurl', TextType(), nullable=False),
    Column('mulefile', TextType(), nullable=True),
    ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
    PrimaryKeyConstraint('id'),
    UniqueConstraint('endpointurl'),
    UniqueConstraint('readmeurl'),
    UniqueConstraint('packageurl')
    )
    op.add_column('workflow', Column('type', EnumerationType(), nullable=True))
    op.execute("update workflow set type = 'yaml' where type IS NULL")
    op.alter_column('workflow', 'type', nullable=False)    
    ### end Alembic commands ###

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'workflow', 'type')
    op.drop_table('workflow_mule')
    ### end Alembic commands ###
