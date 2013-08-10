"""remove old concert workflows

Revision: 2a7c3bf7b40
Revises: 44d13fe72e9e
Created: 2013-08-10 15:05:07.976192
"""

revision = '2a7c3bf7b40'
down_revision = '44d13fe72e9e'

from alembic import op
from spire.schema.fields import *
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("delete from run where workflow_id in "
               "(select id from workflow where (id, name) in ("
               "('00000000-0000-0000-0000-000000002000','create-identification-box'),"
               "('00000000-0000-0000-0000-000000002001','create-artifact'),"
               "('00000000-0000-0000-0000-000000002002','create-collection-box'),"
               "('00000000-0000-0000-0000-000000002003','create-export-box'),"
               "('00000000-0000-0000-0000-000000002004','refine-box'),"
               "('00000000-0000-0000-0000-000000002005','restart-box'),"
               "('00000000-0000-0000-0000-000000002006','clone-box'),"
               "('00000000-0000-0000-0000-000000002007','delete-box')))")

    op.execute("delete from workflow where (id, name) in ("
               "('00000000-0000-0000-0000-000000002000','create-identification-box'),"
               "('00000000-0000-0000-0000-000000002001','create-artifact'),"
               "('00000000-0000-0000-0000-000000002002','create-collection-box'),"
               "('00000000-0000-0000-0000-000000002003','create-export-box'),"
               "('00000000-0000-0000-0000-000000002004','refine-box'),"
               "('00000000-0000-0000-0000-000000002005','restart-box'),"
               "('00000000-0000-0000-0000-000000002006','clone-box'),"
               "('00000000-0000-0000-0000-000000002007','delete-box'))")

def downgrade():
    pass
