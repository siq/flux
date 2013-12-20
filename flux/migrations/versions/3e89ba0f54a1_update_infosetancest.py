"""update infosetancestry workflow infoset query

Revision: 3e89ba0f54a1
Revises: 4d1fb30a5c84
Created: 2013-12-20 09:06:25.426401
"""

revision = '3e89ba0f54a1'
down_revision = '4d1fb30a5c84'

from alembic import op
from sqlalchemy import text

from scheme.formats import Yaml

old_query = {'filter': {'type': 'immutable'}}
new_query = {'type': 'immutable'}

def upgrade():
    connection = op.get_bind()
    fetch_workflows = text("select * from workflow")
    update_workflows = text("update workflow set specification = :spec where id = :id")

    for workflow in connection.execute(fetch_workflows):
        if not workflow.specification:
            continue

        specification = Yaml.unserialize(workflow.specification)
        if not specification or 'schema' not in specification:
            continue

        try:
            query = specification['schema']['structure']['infoset']['source']['query']
        except:
            continue
        if query == old_query:
            specification['schema']['structure']['infoset']['source']['query'] = new_query
            specification = Yaml.serialize(specification)
            connection.execute(update_workflows, spec=specification, id=workflow.id)

def downgrade():
    pass
