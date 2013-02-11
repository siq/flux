from spire.core import Dependency
from spire.mesh import ModelController
from spire.schema import SchemaDependency

from flux.models import *
from flux.resources import Operation as OperationResource

class OperationController(ModelController):
    resource = OperationResource
    version = (1, 0)

    model = Operation
    schema = SchemaDependency('flux')
    mapping = 'id name phase description schema'

    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)

        session.commit()
        response({'id': subject.id})

    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})

        session = self.schema.session
        subject.update(session, **data)

        session.commit()
        response({'id': subject.id})

    def _annotate_resource(self, request, model, resource, data):
        resource['outcomes'] = {}
        for name, outcome in model.outcomes.iteritems():
            resource['outcomes'][name] = outcome.extract_dict(
                exclude='id operation_id name')
