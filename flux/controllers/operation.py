from spire.core import Dependency
from spire.mesh import MeshDependency, ModelController
from spire.schema import NoResultFound, OperationError, SchemaDependency

from flux.engine.queue import QueueManager
from flux.models import *
from flux.operations import *
from flux.resources import Operation as OperationResource

class OperationController(ModelController):
    resource = OperationResource
    version = (1, 0)

    model = Operation
    mapping = 'id name phase description schema parameters'

    schema = SchemaDependency('flux')
    manager = Dependency(QueueManager)

    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)

        self.manager.register(subject)
        session.commit()
        response({'id': subject.id})

    def operation(self, request, response, subject, data):
        operation = OPERATIONS.get(data['subject'])
        if operation:
            operation().execute(self.schema.session, response, data)
        else:
            raise OperationError('invalid-operation')

    def process(self, request, response, subject, data):
        session = self.schema.session
        try:
            execution = WorkflowExecution.load(session, id=data['id'])
        except NoResultFound:
            return # todo: address exception properly

        status = data['status']
        if status in ('completed', 'failed', 'timedout',):
            execution.complete(session, status, data.get('output'))
        elif status == 'progress':
            execution.update_progress(session, data.get('progress'))

        session.commit()

    def task(self, request, response, subject, data):
        task = data['task']
        if task == 'complete-test-operation':
            TestOperation().complete(self.schema.session, data)

    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})

        session = self.schema.session
        subject.update(session, **data)

        self.manager.register(subject)
        session.commit()
        response({'id': subject.id})

    def _annotate_resource(self, request, model, resource, data):
        resource['outcomes'] = {}
        for name, outcome in model.outcomes.iteritems():
            resource['outcomes'][name] = outcome.extract_dict(
                exclude='id operation_id name')
