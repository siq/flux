import scheme
from mesh.standard import GoneError, OperationError, bind
from scheme.surrogate import surrogate
from spire.core import Unit
from spire.mesh import Surrogate, MeshDependency
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.bindings import truss, platoon
from flux.constants import *
from flux.models import EmailTemplate

__all__ = ('Request', 'RequestAttachment', 'RequestSlot', 'RequestProduct')

schema = Schema('flux')
log = LogHelper('flux')

ExternalUrl = bind(truss, 'truss/1.0/externalurl')
Msg = bind(truss, 'truss/1.0/message')

SlotTypes = {
    'text': (scheme.Text, {'type': 'textbox'}),
    'textarea': (scheme.Text, {'type': 'textbox', 'options': {'multiline': True}}),
}

Event = bind(platoon, 'platoon/1.0/event')

class Request(Model):
    """An request."""

    class meta:
        schema = schema
        tablename = 'request'

    id = Identifier()
    name = Text(nullable=False)
    status = Enumeration(REQUEST_STATUSES, nullable=False, default='pending')
    originator = Token(nullable=False)
    assignee = Token(nullable=False)
    creator = Text()
    template_id = ForeignKey('emailtemplate.id')
    slot_order = Array(TextType())
    claimed = DateTime(timezone=True)
    completed = DateTime(timezone=True)

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
            request._setup_slots(request, attrs.get('slot_order'), slots)

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
        slots = self.slots

        key_order = self.slot_order if self.slot_order else slots.keys()
        for token in key_order:
            slot = slots[token]
            field = SlotTypes.get(slot.slot)
            if field:
                fields[token] = field[0]()
                element = {'label': slot.title, 'field': token}
                element.update(field[1])
                elements.append(element)
            else:
                fields[token] = scheme.UUID(nonempty=True, source={
                    'resource': 'docket.entity/1.0/enamel/1.0/infoset',
                })
                elements.append({
                    'field': token,
                    'label': slot.title,
                    'type': 'gridselector',
                })

        return {'schema': scheme.Structure(fields), 'layout': [{'elements': elements}]}

    def decline(self, session):
        assignee = self._get_user(self.assignee)
        if not assignee:
            return

        originator = self._get_user(self.originator)
        if not originator:
            return

        if originator.email:
            try:
                message = self.messages[-1]
            except IndexError:
                message = None
            self._send_decline_email(assignee, originator, message=message)

    def cancel(self, session):
        assignee = self._get_user(self.assignee)
        if not assignee:
            return

        originator = self._get_user(self.originator)
        if not originator:
            return

        if assignee.email:
            self._send_cancel_email(assignee, originator)

    def update(self, session, docket_entity, message=None, **attrs):
        if self.status in ('canceled', 'completed', 'declined'):
            raise OperationError(token='cannot-update-with-status')

        attachments = attrs.pop('attachments', None)
        if attachments:
            self.attachments = []
            for attachment in attachments:
                self.attachments.append(RequestAttachment(**attachment))

        slots = attrs.pop('slots', None)
        if slots:
            self.slots = {}
            session.flush()
            slot_order = attrs.get('slot_order', self.slot_order)
            self._setup_slots(self, slot_order, slots)

        slot_order = attrs.get('slot_order', None)
        if slot_order:
            self._setup_slots(self, slot_order, self.slots)

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
            new_status = self._update_status(status, message)

        self.update_with_mapping(attrs)
        return new_status

    @classmethod
    def reassign_assignee(cls, session, id):
        assigneeRequests = session.query(Request).filter_by(assignee=id)
        for request in assigneeRequests:
            request.assignee = '2533dc9a-0fbe-4ab7-bd10-a65e2ec07cfc' # This is a hardcoded UUID of the super admin's id
            session.call_after_commit(request._request_changed_event, 'request:changed')
        return map(lambda m: m.id, assigneeRequests)

    def _request_changed_event(self, topic):
        try:
            Event.create(topic=topic, aspects={'id': self.id})
        except Exception:
            log('exception', 'failed to fire %s event', topic)
        else:
            log('info', 'fired off %s event for %r', topic, self)

    def _construct_product(self, client, token, id):
        try:
            slot = self.slots[token]
        except KeyError:
            raise OperationError(token='invalid-slot')

        field = SlotTypes.get(slot.slot)
        if field:
            self.products[token] = RequestProduct(
                title=slot.title, token=token,
                product=surrogate.construct(
                    schema=scheme.Structure({'value': field[0](name=token)}),
                    value={'value': id}))

            return
        try:
            product = surrogate.acquire(slot.slot, client=client, id=id)
        except GoneError:
            raise OperationError(token='invalid-product')
        except Exception:
            log('exception', 'failed to acquire product using id %r for token %r' % (id, token))
            raise OperationError(token='cannot-acquire-product')
        else:
            self.products[token] = RequestProduct(title=slot.title, token=token, product=product)

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
            bastion_dependency = BastionDependency()
            Bastion = bastion_dependency.bastion.bind('security/1.0/subject')
            usr = Bastion.get(user_id)
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

        subject = u'New StoredIQ request from %s %s' % (originator.firstname, originator.lastname)
        Msg.create(sender=originator.email, recipients=[{'to': [assignee.email]}],
            subject=subject, body=template.evaluate(params))

    def _send_cancel_email(self, assignee, originator):
        subject = u'StoredIQ request from %s %s is canceled' % (originator.firstname,
            originator.lastname)
        body = u'The request "%s" originated from %s %s has been canceled.' % (self.name,
            originator.firstname, originator.lastname)
        Msg.create(sender=assignee.email, recipients=[{'to': [assignee.email]}],
            subject=subject, body=body)

    def _send_decline_email(self, assignee, originator, message=None):
        message = (message.message or '') if message else ''

        subject = u'StoredIQ request to %s %s is declined' % (
            assignee.firstname, assignee.lastname)
        body = (u'The request "%s" assigned to %s %s has been declined '
                u'with the following fulfillment note: \n%s') % (
                    self.name, assignee.firstname, assignee.lastname, message)

        Msg.create(sender=assignee.email, recipients=[{'to': [originator.email]}],
            subject=subject, body=body)

    @classmethod
    def _setup_slots(cls, request, slot_order, slots):
        slots = slots.copy()
        slot_order = slot_order or slots.keys()
        request_slots = request.slots
        for key in slot_order:
            try:
                value = slots.pop(key)
            except KeyError:
                raise ValidationError('invalid-slot-order')
            if key not in request_slots:
                request_slots[key] = RequestSlot(token=key, **value)
        if slots:
            raise ValidationError('invalid-slot-order')

    def _update_status(self, status, message):
        if self.status == status:
            return

        if self.status == 'prepared':
            if status != 'pending':
                raise ValidationError('invalid-transition')
        elif self.status in ('claimed', 'pending'):
            if status == 'claimed':
                self._validate_message(message, self.assignee)
                self.claimed = scheme.current_timestamp()
            elif status in ('completed', 'declined'):
                if status == 'declined' and not message:
                    raise ValidationError(structure={
                        'message': ValidationError('message-required-for-status')
                    })
                self._validate_message(message, self.assignee)
                self.completed = scheme.current_timestamp()
            elif status == 'canceled':
                self.completed = scheme.current_timestamp()
            else:
                raise ValidationError('invalid-transition')
        else:
            raise ValidationError('invalid-transition')

        self.status = status
        return status

    def _validate_message(self, message, designated_author):
        if message and message['author'] != designated_author:
            raise ValidationError(structure={
                'message': ValidationError('invalid-message-author')
            })

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

class BastionDependency(Unit):
    bastion = MeshDependency('security')
