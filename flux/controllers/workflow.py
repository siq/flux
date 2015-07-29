from mesh.exceptions import OperationError
from mesh.standard import bind
from spire.mesh import ModelController, support_returning
from spire.schema import SchemaDependency, IntegrityError
from spire.support.logs import LogHelper

from flux.bindings import platoon
from flux.models import *
from flux.resources import Workflow as WorkflowResource
from flux.engine.workflow import Workflow as WorkflowEngine

log = LogHelper('flux')
Event = bind(platoon, 'platoon/1.0/event')

class WorkflowController(ModelController):
    resource = WorkflowResource
    version = (1, 0)

    model = Workflow
    mapping = 'id name designation is_service specification modified type'
    schema = SchemaDependency('flux')

    @support_returning
    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)

        try:
            session.commit()
        except IntegrityError:
            raise OperationError(token='duplicate-workflow-name')

        return subject

    def delete(self, request, response, subject, data):
        super(WorkflowController, self).delete(request, response, subject, data)
        self._create_change_event(subject)

    def generate(self, request, response, subject, data):
        name = data['name']
        description = data.get('description', '')
        operations = data['operations']

        specification = {
            'name': name,
            'entry': 'step:0',
        }
        layout = data.get('layout')
        schema = data.get('schema')
        if layout:
            specification['layout'] = layout
        if schema:
            specification['schema'] = schema

        steps = {}
        step_name = None
        for i, op in enumerate(operations):
            new_step_name = 'step:%s' % i
            new_step = {
                'operation': op['operation'],
                'parameters': op['run_params'],
                'description': op.get('description'),
            }
            if step_name:
                steps[step_name]['postoperation'] = [{
                    'actions': [{
                        'action': 'execute-step',
                        'step': new_step_name,
                        'parameters': op.get('step_params'),
                    }],
                    'terminal': False,
                }]

            step_name = new_step_name
            steps[step_name] = new_step

        specification['steps'] = steps
        specification = WorkflowEngine.schema.serialize(specification,
                format='yaml')

        response({'name': name, 'specification': specification, 'description': description})

    @support_returning
    def update(self, request, response, subject, data):
        if not data:
            return subject

        session = self.schema.session
        changed = subject.update(session, **data)

        try:
            session.commit()
        except IntegrityError:
            raise OperationError(token='duplicate-workflow-name')

        if changed:
            self._create_change_event(subject)
        return subject

    def _annotate_resource(self, request, model, resource, data):
        include = data and data.get('include')
        if not include:
            return

        if 'form' in include:
            schema = model.workflow.schema
            layout = model.workflow.layout

            form = {}
            if layout:
                form['layout'] = layout
            if schema:
                form['schema'] = schema

            resource['form'] = form or None

        if 'specification' in include:
            resource['specification'] = model.specification
            
        if 'policies' in include:            
            resource['policies'] = model.policies
            
        if model.type == 'mule':
            resource['mule_extensions'] = model.mule_extensions
            

    def _create_change_event(self, subject):
        try:
            Event.create(topic='workflow:changed', aspects={'id': subject.id})
        except Exception:
            log('exception', 'failed to fire workflow:changed event')
