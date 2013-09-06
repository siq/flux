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

from scheme.formats import Yaml
from alembic import op
from flux.models import Workflow
from sqlalchemy import text

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
    connection = op.get_bind()
    fetch_workflows = text("select * from workflow")
    update_workflows = text("update workflow set specification = :spec where id = :id")
    for wf in connection.execute(fetch_workflows):
        yaml_dict = Yaml.unserialize(wf.specification)
        if yaml_dict.get('form', IncorrectFormDict) == IncorrectFormDict:
            yaml_dict['form'] = CorrectedFormDict
            specification = Yaml.serialize(yaml_dict)
            connection.execute(update_workflows, spec=specification, id=wf.id)

def downgrade():
    pass
