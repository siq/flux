from spire.core import Dependency
from spire.mesh import MeshDependency, ModelController
from spire.schema import NoResultFound, SchemaDependency

from flux.engine.queue import QueueManager
from flux.models import *
from flux.resources import Operation as OperationResource

class OperationController(ModelController):
    resource = OperationResource
    version = (1, 0)

    model = Operation
    mapping = 'id name phase description schema'

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

    def process(self, request, response, subject, data):
        session = self.schema.session
        try:
            execution = Execution.load(session, id=data['id'])
        except NoResultFound:
            return # todo: address exception properly

        status = data['status']
        if status == 'completed':
            execution.complete(session, data.get('output'))
        # TODO: handle process statuses
        elif status == 'failed':
            pass
        elif status == 'progress':
            pass
        elif status == 'timedout':
            pass

        session.commit()

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
