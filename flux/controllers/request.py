from mesh.standard import bind
from spire.mesh import MeshDependency, ModelController, support_returning
from spire.schema import *
from spire.support.logs import LogHelper

from flux.bindings import platoon
from flux.models import EmailTemplate, Message, Request
from flux.operations import *
from flux.resources.request import Request as RequestResource

ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')
Event = bind(platoon, 'platoon/1.0/event')
log = LogHelper('flux')

class RequestController(ModelController):
    resource = RequestResource
    version = (1, 0)
    
    model = Request
    mapping = 'id name status originator assignee template'
    schema = SchemaDependency('flux')
    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')
    
    @support_returning
    def create(self, request, response, subject, data):
        session = self.schema.session       
        message = data.pop('message', None)

        # Need to handle the template first 
        # because we need to insert the id later to the request table
        template = data.pop('template', None)
        if template:
            templateObject = EmailTemplate.put(session, template)

        data['template_id'] = templateObject.id
        subject = self.model.create(session, **data)
        
        try:
            session.flush()
        except IntegrityError:
            raise OperationError(token='duplicate-request-name')
        
        if message:
            Message.create(session, subject.id, **message)

        session.commit()
        
        if subject.status == 'pending':
            ScheduledTask.queue_http_task('initiate-request',
                self.flux.prepare('flux/1.0/request', 'task', None,
                {'task': 'initiate-request', 'id': subject.id}))        

        return subject
    
    def _annotate_resource(self, http_request, model, resource, data):
        resource['attachments'] = attachments = []
        for attachment in model.attachments:
            attachments.append(attachment.extract_dict('token title attachment'))
        
        resource['slots'] = slots = {}
        for key, value in model.slots.iteritems():
            slots[key] = value.extract_dict('title slot')
            
        resource['products'] = products = {}
        for key, value in model.products.iteritems():
            products[key] = value.extract_dict('title product')
            
    @support_returning
    def update(self, request, response, subject, data):
        if not data:
            return subject

        session = self.schema.session
        new_status = subject.update(session, **data)
        session.commit()

        if new_status == 'pending':
            ScheduledTask.queue_http_task('initiate-request',
                self.flux.prepare('flux/1.0/request', 'task', None,
                {'task': 'initiate-request', 'id': subject.id})) 
        elif new_status == 'completed':
            try:
                Event.create(topic='request:completed', aspects={'id': subject.id})  
            except Exception:
                log('exception', 'failed to fire request:completed event')
        return subject 
    
    def task(self, request, response, subject, data):
        session = self.schema.session
        if 'id' in data:
            try:
                subject = self.model.load(session, id=data['id'], lockmode='update')
            except NoResultFound:
                return

        task = data['task']
        if task == 'initiate-request':
            status = subject.initiate(session, subject)            
            if not status:
                subject.status = 'failed'
                try:
                    Event.create(topic='request:completed', aspects={'id': subject.id})  
                except Exception:
                    log('exception', 'failed to fire request:completed event')                
            session.commit() 
        elif task == 'complete-request-operation':
            CreateRequest().complete(session, data)

    def operation(self, request, response, subject, data):
        operation = OPERATIONS.get(data['subject'])
        if operation:
            operation().execute(self.schema.session, response, data)
        else:
            raise OperationError('invalid-subject')