from spire.mesh import ModelController
from spire.schema import *

from flux.resources.emailtemplate import EmailTemplate as EmailTemplateResource
from flux.models.emailtemplate import EmailTemplate

class EmailTemplateController(ModelController):
    resource = EmailTemplateResource
    version = (1, 0)
    
    model = EmailTemplate
    mapping = 'id template'
    schema = SchemaDependency('flux')
    
    def put(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.put(session, **data)
        session.commit()

        return response({'id': subject.id})
