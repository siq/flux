"""add_global_params_to_specifications

Revision: 4761b09ab355
Revises: 30d13bcaabd6
Created: 2013-04-29 17:18:26.906029
"""

revision = '4761b09ab355'
down_revision = '30d13bcaabd6'

import yaml
from alembic import op
from sqlalchemy.orm import sessionmaker
from flux.models import Workflow

FormDict = {
    'schema': {
            'fieldtype': 'structure',
            'structure': {
                    'description' : {
                            'fieldtype' : 'text'
                    },
                    'infoset' : {
                        'fieldtype': 'uuid',
                        'required': 'true',
                        'source' : {
                            'query' : {
                                'filter': {
                                    'type' : 'immutable'
                                }
                            },
                            'resource' : 'docket.entity/1.0/enamel/1.0/infoset'
                        }
                    },
                    'name' : {
                        'fieldtype': 'text',
                        'required': 'true'
                    },
                    'notify' : {
                        'fieldtype': 'email'
                    }
            }
    },
    'layout': [
        {
            'title': 'Base Information',
            'elements': [
                {
                    'field': 'name',
                    'label': 'Base Name (required)',
                    'type': 'textbox'
                },
                {
                    'field': 'description',
                    'label': 'Base Description',
                    'type': 'textbox'
                },
                {
                    'field': 'notify',
                    'label': 'Send email when the process is complete',
                    'type': 'textbox'
                },
            ],
        },
        {
            'title': 'Starting Infoset',
            'elements': [
                {
                     'field': 'infoset',
                     'label': 'Select the starting infoset for this workflow',
                     'type': 'selectbox'
                },
            ],
        }
    ]
}

def upgrade():
    Session = sessionmaker(bind=op.get_bind())
    session = Session()
    workflows = session.query(Workflow).all()
    for wf in workflows:
        try:
            Workflow._verify_specification(wf.specification)
        except Exception, e:
            continue #dont modify invalid workflows
        yaml_dict = yaml.load(wf.specification)
        if not(yaml_dict.get('form')):
            yaml_dict['form'] = FormDict
            wf.specification = yaml.dump(yaml_dict)
    session.commit()

def downgrade():
    pass
