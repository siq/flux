"""refactor_products

Revision: 31b92bf6506d
Revises: 3bf7984d0e85
Created: 2013-06-30 17:48:03.525783
"""

revision = '31b92bf6506d'
down_revision = '3bf7984d0e85'

import yaml
from alembic import op
from spire.schema.fields import *
from spire.mesh import SurrogateType
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from flux.models import Workflow

def upgrade():
    op.create_table('product',
        Column('id', UUIDType(), nullable=False),
        Column('run_id', UUIDType(), nullable=False),
        Column('token', TokenType(), nullable=False),
        Column('product', SurrogateType(), nullable=False),
        ForeignKeyConstraint(['run_id'], ['run.id']),
        PrimaryKeyConstraint('id'),
        UniqueConstraint('run_id','token')
    )
    op.drop_column('run', 'products')

    session = sessionmaker(bind=op.get_bind())()
    for workflow in session.query(Workflow).all():
        workflow.specification = (workflow.specification
            .replace('${step.out.infoset}', '${step.out.infoset.id}')
            .replace('${step.out.node_count}', '${step.out.infoset.node_count}')
            .replace('${step.out.execution}', '${step.out.execution.id}')
            .replace('${step.out.exception_ratio}', '${step.out.execution.exception_ratio}'))
    session.flush()

def downgrade():
    op.add_column('run', Column('products', TextType(), nullable=True))
    op.drop_table('product')
