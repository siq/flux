from spire.mesh import ModelController
from spire.schema import *
from flux.resources.request import Request as RequestResource
from flux.models.request import Request
from flux.models.message import Message

class RequestController(ModelController):
    resource = RequestResource
    version = (1, 0)
    
    model = Request
    mapping = 'id name status originator assignee'
    schema = SchemaDependency('flux')
    
    @support_returning
    def create(self, request, response, subject, data):
        session = self.schema.session
        message = data.pop('message', None)
        subject = self.model.create(session, **data)
        
        try:
            session.flush()
        except IntegrityError:
            raise OperationError(token='duplicate-request-name')
        
        if message:
            Message.create(session, subject.id, **message)

        session.commit()

        return subject