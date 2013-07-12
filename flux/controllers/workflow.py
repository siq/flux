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
    mapping = 'id name designation specification modified'
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

    def generate(self, request, response, subject, data):
        name = data['name']
        description = data.get('description', '')
        operations = data['operations']

        specification = {'name': name, 'entry': 'step:0'}
        form = data.get('form')
        if form:
            specification['form'] = form

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
        subject.update(session, **data)

        try:
            session.commit()
        except IntegrityError:
            raise OperationError(token='duplicate-workflow-name')
        try:
            Event.create(topic='workflow:changed', aspects={'id': self.id})
        except Exception:
            log('exception', 'failed to fire workflow:changed event')
        return subject

    def _annotate_resource(self, request, model, resource, data):
        include = data and data.get('include')
        if not include:
            return

        if 'form' in include:
            form = model.workflow.form
            if form:
                resource['form'] = form.extract_dict()
            else:
                resource['form'] = None
        if 'specification' in include:
            resource['specification'] = model.specification
