import scheme
from mesh.standard import GoneError, OperationError, bind
from scheme.surrogate import surrogate
from spire.core import Unit
from spire.mesh import Surrogate, MeshDependency
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.bindings import truss
from flux.constants import *
from flux.models import EmailTemplate

__all__ = ('Request', 'RequestAttachment', 'RequestSlot', 'RequestProduct')

schema = Schema('flux')
log = LogHelper('flux')

ExternalUrl = bind(truss, 'truss/1.0/externalurl')
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
    template_id = ForeignKey('emailtemplate.id')

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
    template = relationship('EmailTemplate')

    def initiate(self, session):
        assignee = self._get_user(self.assignee)
        if not assignee:
            return False

        originator = self._get_user(self.originator)
        if not originator:
            return False

        if assignee.email:
            self._send_init_email(session, assignee, originator)
            return True
        else:
            return False

    @classmethod
    def create(cls, session, attachments=None, slots=None, template=None, **attrs):
        template_id = None
        if template:
            template_id = EmailTemplate.put(session, template).id

        request = cls(template_id=template_id, **attrs)
        if attachments:
            for attachment in attachments:
                request.attachments.append(RequestAttachment(**attachment))

        if slots:
            for key, value in slots.iteritems():
                request.slots[key] = RequestSlot(token=key, **value)

        session.add(request)
        return request

    def generate_entities(self):
        entities = {}
        for token, product in self.products.iteritems():
            entities[token] = product.product['id']
        return entities

    def generate_form(self):
        fields = {}
        elements = []

        for token, slot in self.slots.iteritems():
            fields[token] = scheme.UUID(nonempty=True, source={
                'resource': 'docket.entity/1.0/enamel/1.0/infoset',
                'query': {'filter': {'type': 'immutable'}},
            })
            elements.append({
                'field': token,
                'label': slot.title,
                'type': 'gridselector',
            })

        return {'schema': scheme.Structure(fields), 'layout': [{'elements': elements}]}

    def update(self, session, docket_entity, **attrs):
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

        entities = attrs.pop('entities', None)
        if entities:
            self.products = {}
            session.flush()
            for token, id in entities.iteritems():
                self._construct_product(docket_entity, token, id)

        new_status = None
        status = attrs.pop('status', None)
        if status:
            new_status = self._update_status(status)

        self.update_with_mapping(attrs)
        return new_status

    def _construct_product(self, client, token, id):
        try:
            slot = self.slots[token]
        except KeyError:
            raise OperationError(token='invalid-slot')

        try:
            product = surrogate.acquire(slot.slot, client=client, id=id)
        except GoneError:
            raise OperationError(token='invalid-product')
        except Exception:
            log('exception', 'failed to acquire product using id %r for token %r' % (id, token))
            raise OperationError(token='cannot-acquire-product')
        else:
            self.products[token] = RequestProduct(token=token, product=product)

    def _convert_request_to_dict(self):
        resource = self.extract_dict(attrs='id name status originator assignee')

        resource['attachments'] = attachments = []
        for attachment in self.attachments:
            attachments.append(attachment.extract_dict('token title attachment'))

        resource['slots'] = slots = {}
        for key, value in self.slots.iteritems():
            slots[key] = value.extract_dict('title slot')

        return resource

    def _get_user(self, user_id):
        try:
            docket_dependency = DocketDependency()
            DocketSubject = docket_dependency.docket_entity.bind('docket.entity/1.0/security/1.0/subject')
            usr = DocketSubject.get(user_id)
            return usr
        except Exception:
            log('exception', 'failed to retrieve user subject with user id "%s"' % user_id)

    def _send_init_email(self, session, assignee, originator):
        template = self.template
        if not template:
            raise Exception('invalid template')

        params = {}

        # this is a horrible, horrible, horrible hack
        enamel_concept_client = DocketDependency().enamel_concept
        params['enamel_concept_client'] = enamel_concept_client

        params['request'] = self.extract_dict(attrs='id name status originator assignee')
        params['request']['url'] = ExternalUrl.create(path='/complete-request/%s' % self.id).url

        params['originator'] = originator.extract_dict('id name firstname lastname email')
        params['assignee'] = assignee.extract_dict('id name firstname lastname email')

        params['attachments'] = attachments = {}
        for attachment in self.attachments:
            attachment = attachment.extract_dict('token title attachment')
            if attachment['token'] in attachments:
                attachments[attachment['token']].append(attachment)
            else:
                attachments[attachment['token']] = [attachment]

        params['slots'] = slots = {}
        for token, slot in self.slots.iteritems():
            slots[token] = slot.extract_dict('title slot')

        subject = 'New StoredIQ request from %s %s' % (originator.firstname, originator.lastname)
        Msg.create(sender=originator.email, recipients=[{'to': [assignee.email]}],
            subject=subject, body=template.evaluate(params))

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
    enamel_concept = MeshDependency('enamel.concept')
