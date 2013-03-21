"""unique workflow name

Revision: 83ac97de615
Revises: 270148ec7ba7
Created: 2013-03-21 14:27:28.659710
"""

revision = '83ac97de615'
down_revision = '270148ec7ba7'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint, CheckConstraint
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute('create temp sequence uniquefier')
    op.execute("update workflow set name = name || ' (' || nextval('uniquefier')"
        " || ')' where name in (select name from workflow group by name"
        " having count(name) > 1)")
    op.create_unique_constraint('workflow_name_unique_key', 'workflow', ['name'])

def downgrade():
    op.drop_constraint('workflow_name_unique_key', 'workflow')
