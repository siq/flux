"""remove exisiting workflow excluding concerts

Revision: 384bb0af702c
Revises: 2b783cf338a3
Created: 2013-09-11 10:28:06.123848
"""

revision = '384bb0af702c'
down_revision = '2b783cf338a3'

from alembic import op
from spire.schema.fields import *
from sqlalchemy import (Column, ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint,
    CheckConstraint, UniqueConstraint)
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute("delete from execution where run_id in "
               "(select id from run where workflow_id in "
               "(select id from workflow where (id, name) not in ("
               "('c9741c48-6125-4fbf-a771-0e4107ddc27e','create-identification-box'),"
               "('050bf831-4087-4f04-b657-1038d3daca98','create-artifact'),"
               "('5f02c8bd-6e78-49c0-8bdf-468898a919ea','create-collection-box'),"
               "('833919a0-fb4d-44d7-b40f-103ab5a37f82','create-export-box'),"
               "('db82cdc6-e832-4b12-910a-47eb13da6e90','refine-box'),"
               "('d4e08a73-77e1-48ae-8e81-79d464d380e6','restart-box'),"
               "('b1a784c0-1399-4592-959f-92150116a6f9','clone-box'),"
               "('784f6525-b83a-4789-ae09-7c0808d9ca33','delete-box'))))")

    op.execute("delete from product where run_id in "
               "(select id from run where workflow_id in "
               "(select id from workflow where (id, name) not in ("
               "('c9741c48-6125-4fbf-a771-0e4107ddc27e','create-identification-box'),"
               "('050bf831-4087-4f04-b657-1038d3daca98','create-artifact'),"
               "('5f02c8bd-6e78-49c0-8bdf-468898a919ea','create-collection-box'),"
               "('833919a0-fb4d-44d7-b40f-103ab5a37f82','create-export-box'),"
               "('db82cdc6-e832-4b12-910a-47eb13da6e90','refine-box'),"
               "('d4e08a73-77e1-48ae-8e81-79d464d380e6','restart-box'),"
               "('b1a784c0-1399-4592-959f-92150116a6f9','clone-box'),"
               "('784f6525-b83a-4789-ae09-7c0808d9ca33','delete-box'))))")

    op.execute("delete from run where workflow_id in "
               "(select id from workflow where (id, name) not in ("
               "('c9741c48-6125-4fbf-a771-0e4107ddc27e','create-identification-box'),"
               "('050bf831-4087-4f04-b657-1038d3daca98','create-artifact'),"
               "('5f02c8bd-6e78-49c0-8bdf-468898a919ea','create-collection-box'),"
               "('833919a0-fb4d-44d7-b40f-103ab5a37f82','create-export-box'),"
               "('db82cdc6-e832-4b12-910a-47eb13da6e90','refine-box'),"
               "('d4e08a73-77e1-48ae-8e81-79d464d380e6','restart-box'),"
               "('b1a784c0-1399-4592-959f-92150116a6f9','clone-box'),"
               "('784f6525-b83a-4789-ae09-7c0808d9ca33','delete-box')))")

    op.execute("delete from workflow where (id, name) not in ("
               "('c9741c48-6125-4fbf-a771-0e4107ddc27e','create-identification-box'),"
               "('050bf831-4087-4f04-b657-1038d3daca98','create-artifact'),"
               "('5f02c8bd-6e78-49c0-8bdf-468898a919ea','create-collection-box'),"
               "('833919a0-fb4d-44d7-b40f-103ab5a37f82','create-export-box'),"
               "('db82cdc6-e832-4b12-910a-47eb13da6e90','refine-box'),"
               "('d4e08a73-77e1-48ae-8e81-79d464d380e6','restart-box'),"
               "('b1a784c0-1399-4592-959f-92150116a6f9','clone-box'),"
               "('784f6525-b83a-4789-ae09-7c0808d9ca33','delete-box'))")

def downgrade():
    pass
