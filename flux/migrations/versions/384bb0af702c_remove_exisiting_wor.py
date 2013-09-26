"""remove exisiting workflow excluding concerts

Revision: 384bb0af702c
Revises: 2b783cf338a3
Created: 2013-09-11 10:28:06.123848
"""

revision = '384bb0af702c'
down_revision = '2b783cf338a3'

from alembic import op
from sqlalchemy import text

from scheme.formats import Yaml

def _has_operation(steps, operation):
    for step in steps.itervalues():
        if step['operation'] == operation:
            return True
    return False

def upgrade():
    connection = op.get_bind()
    fetch_workflows = text("select * from workflow")
    delete_executions = text(
        "delete from execution where run_id in (select id from run where workflow_id = :id)")
    delete_products = text(
        "delete from product where run_id in (select id from run where workflow_id = :id)")
    delete_runs = text(
        "delete from run where workflow_id in (select id from workflow where id = :id)")
    delete_workflow = text("delete from workflow where id = :id")

    for wf in connection.execute(fetch_workflows):
        yaml = Yaml.unserialize(wf.specification)
        schema = yaml.get('schema')
        steps = yaml.get('steps')
        if wf.is_service or not (schema and steps):
            continue
        if _has_operation(steps, 'create-infoset') and 'document_id' not in schema:
            connection.execute(delete_executions, id=wf.id)
            connection.execute(delete_products, id=wf.id)
            connection.execute(delete_runs, id=wf.id)
            connection.execute(delete_workflow, id=wf.id)

def downgrade():
    pass
