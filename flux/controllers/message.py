from spire.mesh import ModelController
from spire.schema import *
from flux.resources.message import Message as MessageResource
from flux.models.message import Message

class MessageController(ModelController):
    resource = MessageResource
    version = (1, 0)
    
    model = Message
    mapping = 'id request_id author occurrence message'
    schema = SchemaDependency('flux')
    
    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)
        session.commit()

        return response({'id': subject.id})
        
    def update(self, request, response, subject, data):
        if not data:
            return response({'id': subject.id})
            
        session = self.schema.session
        subject.update_with_mapping(data)
        session.commit()

        return response({'id': subject.id})