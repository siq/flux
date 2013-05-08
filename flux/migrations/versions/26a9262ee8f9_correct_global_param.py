"""correct_global_params_on_workflow_specification

Revision: 26a9262ee8f9
Revises: 4761b09ab355
Created: 2013-05-07 16:48:13.635359

Differences in the two specifications are:
1. the multiline option on the description
2. the gridselector type on the infoset element
3. values that were 'true' are now True
"""

revision = '26a9262ee8f9'
down_revision = '4761b09ab355'

import yaml
from alembic import op
from sqlalchemy.orm import sessionmaker
from flux.models import Workflow

IncorrectFormDict = {
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

CorrectedFormDict = {
    'schema': {
            'fieldtype': 'structure',
            'structure': {
                    'description' : {
                            'fieldtype' : 'text'
                    },
                    'infoset' : {
                        'fieldtype': 'uuid',
                        'required': True,
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
                        'required': True
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
                    'type': 'textbox',
                    'options': {
                        'multiline': True
                    }
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
                     'type': 'gridselector'
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
        if yaml_dict.get('form', IncorrectFormDict) == IncorrectFormDict:
            yaml_dict['form'] = CorrectedFormDict
            wf.specification = yaml.dump(yaml_dict)
    session.commit()

def downgrade():
    pass
