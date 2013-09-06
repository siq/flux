"""replace workflow form field

Revision: 1d949e7fe5a1
Revises: 9ba67b798fa
Created: 2013-07-26 18:05:35.473903
"""

revision = '1d949e7fe5a1'
down_revision = '9ba67b798fa'

from alembic import op
from sqlalchemy import text

from scheme.formats import Yaml
from flux.models import Workflow

def upgrade():
    connection = op.get_bind()
    fetch_workflows = text("select * from workflow")
    update_workflows = text("update workflow set specification = :spec where id = :id")

    for workflow in connection.execute(fetch_workflows):
        if not workflow.specification:
            continue
        specification = Yaml.unserialize(workflow.specification)
        if not specification or 'form' not in specification:
            continue

        form = specification.pop('form')
        if 'schema' in form:
            specification['schema'] = form['schema']
            
        if 'layout' in form:
            specification['layout'] = form['layout']

        specification = Yaml.serialize(specification)
        connection.execute(update_workflows, spec=specification, id=workflow.id)

def downgrade():
    pass
