"""add_mule_extensions

Revision: 1aba5fdfaebe
Revises: 494215ec15e4
Created: 2015-07-30 08:01:27.942569
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
        Column('packageurl', TextType(), nullable=False),
        Column('endpointurl', TextType(), nullable=False),
        Column('readmeurl', TextType(), nullable=True),
        ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ondelete='CASCADE'),
        PrimaryKeyConstraint('id'),
        UniqueConstraint('endpointurl'),
        UniqueConstraint('packageurl'),
        UniqueConstraint('readmeurl')
    )
    op.add_column('workflow', Column('type', EnumerationType(), nullable=True))
    op.execute("update workflow set type = 'yaml'")
    op.alter_column('workflow', 'type', nullable=False)
    ### end Alembic commands ###

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'workflow', 'type')
    op.drop_table('workflow_mule')
    ### end Alembic commands ###