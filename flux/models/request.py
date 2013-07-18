from mesh.standard import OperationError, bind
from scheme import current_timestamp
from spire.mesh import Surrogate
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.constants import *

__all__ = ('Request', 'RequestAttachment', 'RequestSlot', 'RequestProduct')

schema = Schema('flux')
log = LogHelper('flux')

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