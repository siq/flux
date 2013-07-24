from mesh.standard import OperationError, bind
from scheme import current_timestamp
from spire.core import Unit
from spire.mesh import Surrogate, MeshDependency
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.constants import *
from flux.bindings import truss

__all__ = ('Request', 'RequestAttachment', 'RequestSlot', 'RequestProduct')

schema = Schema('flux')
log = LogHelper('flux')
Msg = bind(truss, 'truss/1.0/message')

class Request(Model):
    """An request."""

    class meta:
        schema = schema
        tablename = 'request'

    id = Identifier()
    name = Text(nullable=False, unique=True)
    status = Enumeration(REQUEST_STATUSES, nullable=False, default='pending')
    originator = Token(nullable=False)
    assignee = Token(nullable=False)
    
    attachments = relationship('RequestAttachment', cascade='all,delete-orphan', 
                               passive_deletes=True, backref='request')
    slots = relationship('RequestSlot', cascade='all,delete-orphan', 
                               passive_deletes=True, backref='request',
                               collection_class=attribute_mapped_collection('token'))
    products = relationship('RequestProduct', cascade='all,delete-orphan', 
                               passive_deletes=True, backref='request',
                               collection_class=attribute_mapped_collection('token'))    
    messages = relationship('Message', cascade='all,delete-orphan', 
                               passive_deletes=True, backref='request')
    
    @classmethod
    def create(cls, session, attachments=None, slots=None, **attrs):
        request = cls(**attrs)
        if attachments:
            for attachment in attachments:
                request.attachments.append(RequestAttachment(**attachment))
        
        if slots:
            for key, value in slots.iteritems():
                request.slots[key] = RequestSlot(token=key, **value)
                
        session.add(request)
        
        return request
    
    def update(self, session, **attrs):
        attachments = attrs.pop('attachments', None)
        if attachments:
            self.attachments = []            
            for attachment in attachments:
                self.attachments.append(RequestAttachment(**attachment))

        slots = attrs.pop('slots', None)
        if slots:
            self.slots = {}
            session.flush()
            for key, value in slots.iteritems():
                self.slots[key] = RequestSlot(token=key, **value)

        products = attrs.pop('products', None)
        if products:
            self.products = {}
            session.flush()
            for key, value in products.iteritems():
                self.products[key] = RequestProduct(token=key, **value)

        # assuming message is not specified during update

        new_status = None
        status = attrs.pop('status', None)
        if status:
            new_status = self._update_status(status)
        
        self.update_with_mapping(attrs)
        return new_status
    
    def _update_status(self, status):
        if self.status == status:
            return
        
        if self.status == 'prepared':
            if status == 'pending':
                self.status = status
                return status
            else:
                raise ValidationError('invalid-transition')
        elif self.status == 'pending':
            if status == 'completed':
                self.status = status
                return status
            else:
                raise ValidationError('invalid-transition')
        
    def initiate(self, session, subject):
        assignee = self._get_user(subject.assignee)
        if not assignee:
            return False
        originator = self._get_user(subject.originator)
        if not originator:
            return False
        
        if assignee.email:
            self._send_init_email(subject, assignee, originator)
            return True
        else:
            return False
        
    def _get_user(self, user_id):
        try:
            docket_dependency = DocketDependency()
            DocketSubject = docket_dependency.docket_entity.bind('docket.entity/1.0/security/1.0/subject')            
            usr = DocketSubject.get(user_id)
            return usr
        except Exception:
            log('exception', 'failed to retrieve user subject with user id "%s"' % user_id)
            return        

    def _send_init_email(self, subject, assignee, originator):
        sender = originator.email
        recipients = [{'to': assignee.email.split(',')}]
        email_subject = 'Request "%s" initiated' % self.name
        body = 'The request named "%s" has been initiated.' % self.name
        Msg.create(sender=sender, recipients=recipients, subject=email_subject, body=body) 
        
class RequestAttachment(Model):
    """An attachment."""

    class meta:
        schema = schema
        tablename = 'request_attachment'

    id = Identifier()
    request_id = ForeignKey('request.id', nullable=False, ondelete='CASCADE')
    token = Token()
    title = Text()
    attachment = Surrogate(nullable=False)
    
class RequestSlot(Model):
    """An slot."""

    class meta:
        constraints = [UniqueConstraint('request_id', 'token')]
        schema = schema
        tablename = 'request_slot'

    id = Identifier()
    request_id = ForeignKey('request.id', nullable=False, ondelete='CASCADE')
    token = Token(nullable=False)
    title = Text()
    slot = Token(nullable=False)

class RequestProduct(Model):
    """An product."""

    class meta:
        constraints = [UniqueConstraint('request_id', 'token')]
        schema = schema
        tablename = 'request_product'

    id = Identifier()
    request_id = ForeignKey('request.id', nullable=False, ondelete='CASCADE')
    token = Token(nullable=False)
    title = Text()
    product = Surrogate(nullable=False)
    
class DocketDependency(Unit):
    docket_entity = MeshDependency('docket.entity')