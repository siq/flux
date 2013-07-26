"""replace workflow form field

Revision: 1d949e7fe5a1
Revises: 9ba67b798fa
Created: 2013-07-26 18:05:35.473903
"""

revision = '1d949e7fe5a1'
down_revision = '9ba67b798fa'

from alembic import op
from sqlalchemy.orm import sessionmaker

from scheme.formats import Yaml
from flux.models import Workflow

def upgrade():
    session = sessionmaker(bind=op.get_bind())()
    for workflow in session.query(Workflow).all():
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

        workflow.specification = Yaml.serialize(specification)

    session.commit()

def downgrade():
    pass
