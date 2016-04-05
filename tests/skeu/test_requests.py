from datetime import datetime
from time import sleep

from scheme import current_timestamp, fields
from scheme.surrogate import surrogate
from spire.core import adhoc_configure, Unit
from spire.mesh import MeshDependency
from spire.schema import SchemaDependency
from mesh.testing import MeshTestCase
from mesh.exceptions import GoneError, InvalidError, OperationError

from flux.bundles import API
from flux.engine.rule import RuleList
from flux.models import Request


adhoc_configure({
    'schema:flux': {
        'url': 'postgresql://postgres@localhost/flux'
    },
    'mesh:flux': {
        'url': 'http://localhost:9997/',
        'bundle': 'flux.API',
    },
    'mesh:docket': {
        'url': 'http://localhost:9998/',
        'specification': 'flux.bindings.docket.specification',
    },
    'mesh:docket.entity': {
        'url': 'http://localhost:9998/',
        'introspect': True,
    },
    'mesh:platoon': {
        'url': 'http://localhost:4321/',
        'specification': 'flux.bindings.platoon.specification',
    },
    'mesh:truss': {
        'url': 'http://localhost:9999/api',
        'specification': 'flux.bindings.truss.specification',
    },
})


_LOGIN_CONTEXT = {
    'credential-type': 'password',
    'credential-username': 'superadmin',
    'credential-password': 'admin',
    'credential-tenant-id': 'bastion.security'
}


class TestDependency(Unit):
    schema = SchemaDependency('flux')
    docket_entity = MeshDependency('docket.entity')


class BaseTestCase(MeshTestCase):
    bundle = API
    maxDiff = None
    config = TestDependency()

    def setUp(self):
        self._requests = set()
        self._users = set()

    def tearDown(self):
        session = self.config.schema.session
        model_instances = (
            (self._requests, Request),
        )
        for model_ids, model in model_instances:
            for model_id in model_ids:
                try:
                    session.delete(model.load(session, id=model_id))
                    session.commit()
                except:
                    session.rollback()
                    continue

        self._destroy_user(*self._users)

    def _destroy_user(self, *users):
        client = self.config.docket_entity.instance
        client.context_header_prefix = 'X-SPIRE-'
        for user_id in users:
            if not user_id:
                continue
            try:
                resp = client.execute('docket.entity/1.0/security/1.0/subject',
                    'delete', context=_LOGIN_CONTEXT, subject=user_id)
            except GoneError:
                continue
            if resp.status != 'OK':
                raise Exception('failed to delete bastion subject: %s')

    def _setup_request(self, client, **data):
        resp = client.execute('request', 'create', data=data)
        try:
            request_id = resp.content['id']
        except (AttributeError, KeyError):
            pass
        else:
            self._requests.add(request_id)
        return resp

    def _setup_request_and_change_status(
            self, client, name, template,
            new_status, **kwargs):
        originator = (
            kwargs.get('originator') or
            self._setup_user(
                name='originator',
                email='originator@localhost.local'
            ).content['id']
        )

        assignee = (
            kwargs.get('assignee') or
            self._setup_user(
                name='assignee',
                email='assignee@localhost.local'
            ).content['id']
        )

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = client.execute(
            'request', 'update',
            subject=request_id, data={'status': new_status}
        )
        self.assertEquals(resp.status, 'OK')

        return request_id

    def _setup_user(self, **attrs):
        client = self.config.docket_entity.instance
        client.context_header_prefix = 'X-SPIRE-'

        name = attrs['name']
        firstname = attrs.get('firstname', 'Last')
        lastname = attrs.get('lastname', 'First')
        email = attrs['email']
        roles = attrs.get('roles', ['appstack:admin-user'])
        domain_id = attrs.get('domain_id', '96af6071-f859-40cf-a9f9-23b7c38d6b9c')
        credential = attrs.get('credential', {'type': 'password', 'password': 'Abcd-1234'})

        resp = client.execute('docket.entity/1.0/security/1.0/subject',
            'create', context=_LOGIN_CONTEXT, data={
                'domain_id': domain_id,
                'name': name, 'firstname': firstname, 'lastname': lastname,
                'roles': roles, 'email': email, 'credential': credential,
            }
        )
        try:
            user_id = resp.content['id']
        except (AttributeError, KeyError):
            pass
        else:
            self._users.add(user_id)
        return resp


class PendingRequestTest(BaseTestCase):
    """Request in pending state test cases"""

    def test_pending_request(self, client):
        """Test case for creating request in pending state, the default state"""
        name = 'test pending request'
        template = 'test pending request template'
        creator = 'Jane L Creator'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, creator=creator, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'pending',
            'template': template,
            'creator': creator,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        result = resp.content
        self.assertEquals(result, expected)

    def test_claiming_pending_request(self, client):
        """Test case for updating pending request to claimed"""
        name = 'test claiming pending request'
        template = 'test claiming pending request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template,
            status='pending'
        )
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = client.execute(
            'request', 'update',
            subject=request_id, data={'status': 'claimed'}
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'claimed',
            'template': template,
            'creator': None,
            'completed': None,
        }
        resp = client.execute(
            'request', 'get', subject=request_id,
            data={'include': ['template']}
        )
        result = resp.content
        self.assertTrue(isinstance(result.pop('claimed', None), datetime))
        self.assertEquals(result, expected)

    def test_completing_pending_request(self, client):
        """Test case for successfully updating a pending request to a completed state"""
        name = 'test completing pending request'
        template = 'test completing pending request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = client.execute('request', 'update', subject=request_id,
            data={'status': 'completed'})
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'completed',
            'template': template,
            'creator': None,
            'claimed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)

    def test_cancelling_pending_request(self, client):
        """Test case for successfully updating a pending request to a canceled state"""
        name = 'test cancelling pending request'
        template = 'test cancelling pending template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = client.execute('request', 'update', subject=request_id,
            data={'status': 'canceled'})
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'canceled',
            'template': template,
            'creator': None,
            'claimed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)

    def test_declining_pending_request(self, client):
        """Test case for successfully updating a pending request to a declined state"""
        name = 'test declining pending request'
        template = 'test declining pending request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = client.execute(
            'request', 'update', subject=request_id,
            data={
                'status': 'declined',
                'message': {
                    'author': assignee,
                    'message': 'Declined status message'
                }
            }
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'declined',
            'template': template,
            'creator': None,
            'claimed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)


class PreparedRequestTest(BaseTestCase):
    """Request in prepared state test cases"""

    def test_prepared_request(self, client):
        """Test case for creating a request in prepared state"""
        name = 'test prepared request'
        template = 'test prepared request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template, status='prepared')
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'prepared',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        result = resp.content
        self.assertEquals(result, expected)

    def test_completing_prepared_request(self, client):
        """Test case for handling failed update to a completed state"""
        name = 'test completing prepared request'
        template = 'test completing prepared request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template , status='prepared')
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-transition'):
            client.execute('request', 'update', subject=request_id, data={'status': 'completed'})

    def test_cancelling_prepared_request(self, client):
        """Test case for handling failed update to a canceled state"""
        name = 'test cancelling prepared request'
        template = 'test cancelling prepared request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template, status='prepared')
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-transition'):
            client.execute('request', 'update', subject=request_id, data={'status': 'canceled'})

    def test_claiming_prepared_request(self, client):
        """Test case for updating prepared request to claimed"""
        name = 'test claiming prepared request'
        template = 'test claiming prepared request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template,
            status='prepared'
        )
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-transition'):
            client.execute(
                'request', 'update',
                subject=request_id, data={'status': 'claimed'}
            )

    def test_declining_prepared_request(self, client):
        """Test case for handling failed update to a declined state"""
        name = 'test declining prepared request'
        template = 'test declining prepared request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template, status='prepared')
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-transition'):
            client.execute(
                'request', 'update',
                subject=request_id,
                data={
                    'status': 'declined',
                    'message': {
                        'author': assignee,
                        'message': 'Declined status message'
                    }
                })

class ClaimedRequestTest(BaseTestCase):
    """Request in claimed state test case"""
    def test_claimed_request_status(self, client):
        """Test case for claimed status on request"""
        name = 'test claimed request'
        template = 'test claimed request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        request_id = self._setup_request_and_change_status(
            client, name, template, 'claimed',
            originator=originator, assignee=assignee)

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'claimed',
            'template': template,
            'creator': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('claimed', None), datetime))
        self.assertEquals(result, expected)

    def test_cancelling_claimed_request(self, client):
        """Test case for updating claimed request to canceled status"""
        name = 'test cancelling claimed request'
        template = 'test cancelling claimed request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        request_id = self._setup_request_and_change_status(
            client, name, template, 'claimed',
            originator=originator, assignee=assignee)

        resp = client.execute(
            'request', 'update',
            subject=request_id, data={'status': 'canceled'}
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'canceled',
            'template': template,
            'creator': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('claimed', None), datetime))
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)

    def test_completing_claimed_request(self, client):
        """Test case for updating claimed request to completed status"""
        name = 'test completing claimed request'
        template = 'test completing claimed request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        request_id = self._setup_request_and_change_status(
            client, name, template, 'claimed',
            originator=originator, assignee=assignee)

        resp = client.execute(
            'request', 'update',
            subject=request_id, data={'status': 'completed'}
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'completed',
            'template': template,
            'creator': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('claimed', None), datetime))
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)

    def test_declining_claimed_request(self, client):
        """Test case for updating claimed request to declined status"""
        name = 'test declining claimed request'
        template = 'test declining claimed request template'
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        request_id = self._setup_request_and_change_status(
            client, name, template, 'claimed',
            originator=originator, assignee=assignee)

        resp = client.execute(
            'request', 'update',
            subject=request_id,
            data={
                'status': 'declined',
                'message': {
                    'author': assignee,
                    'message': 'Declined status message'
                },
            }
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'declined',
            'template': template,
            'creator': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
                data={'include': ['template']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('claimed', None), datetime))
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)


class RequestSlotTest(BaseTestCase):
    """Request slot test cases"""

    def test_bad_slot_order_value(self, client):
        """Test slot_order with invalid slot token"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1', 'bad-slot']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-slot-order'):
            self._setup_request(client, name=name, originator=originator, assignee=assignee,
                template=template, slots=slots, slot_order=slot_order)

    def test_extra_slot_order_token(self, client):
        """Test slot_order with an extra slot token"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1', 'slot2', 'extra-token']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-slot-order'):
            self._setup_request(client, name=name, originator=originator, assignee=assignee,
                template=template, slots=slots, slot_order=slot_order)

    def test_missing_slot_order_token(self, client):
        """Test slot_order with a missing slot token"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1',]
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        with self.assertRaisesRegexp(InvalidError, 'invalid-slot-order'):
            self._setup_request(client, name=name, originator=originator, assignee=assignee,
                template=template, slots=slots, slot_order=slot_order)

    def test_valid_slot_order_tokens(self, client):
        """Test slot_order with valid slot tokens"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'},
            'slot3': {'title': 'Slot 3', 'slot': 'enamel.surrogates.infoset'},
        }
        slot_order = ['slot3', 'slot2', 'slot1']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator, assignee=assignee,
            template=template, slots=slots, slot_order=slot_order)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': slot_order,
            'slots': slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
            'form': {
                'layout': [
                    {
                        'elements': [
                            {
                                'field': 'slot3',
                                'label': 'Slot 3',
                                'type': 'gridselector',
                            },
                            {
                                'field': 'slot2',
                                'label': 'Slot 2',
                                'type': 'gridselector',
                            },
                            {
                                'field': 'slot1',
                                'label': 'Slot 1',
                                'type': 'gridselector',
                            },
                        ]
                    },
                ],
                'schema': fields.Structure(structure={
                    'slot1': fields.UUID(name='slot1', nonempty=True,
                        source={'resource': 'docket.entity/1.0/enamel/1.0/infoset'}),
                    'slot2': fields.UUID(name='slot2', nonempty=True,
                        source={'resource': 'docket.entity/1.0/enamel/1.0/infoset'}),
                    'slot3': fields.UUID(name='slot3', nonempty=True,
                        source={'resource': 'docket.entity/1.0/enamel/1.0/infoset'}),
                }),
            },
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template', 'form']})
        result = resp.content
        result_schema = result['form'].pop('schema').describe()
        expected_schema  = expected['form'].pop('schema').describe()
        self.assertEquals(result_schema, expected_schema)
        self.assertEquals(result, expected)

    def test_valid_update_slot_order(self, client):
        """Test valid update of slot_order"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1', 'slot2']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator, assignee=assignee,
            template=template, slots=slots, slot_order=slot_order)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        initial_expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': slot_order,
            'slots': slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        initial_result = resp.content
        self.assertEquals(initial_result, initial_expected)

        new_slot_order = ['slot2', 'slot1']
        resp = client.execute('request', 'update', data={'slot_order': new_slot_order},
            subject=request_id)

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': new_slot_order,
            'slots': slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        result = resp.content
        self.assertEquals(result, expected)

    def test_valid_update_slots_with_slot_order(self, client):
        """Test valid update of slots with a slot_order"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1', 'slot2']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator, assignee=assignee,
            template=template, slots=slots, slot_order=slot_order)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        initial_expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': slot_order,
            'slots': slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        initial_result = resp.content
        self.assertEquals(initial_result, initial_expected)

        new_slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'textarea'}
        }
        resp = client.execute('request', 'update', data={'slots': new_slots},
            subject=request_id)

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': slot_order,
            'slots': new_slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        result = resp.content
        self.assertEquals(result, expected)

    def test_update_slot_order_nullify(self, client):
        """Test update slot_order to null"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1', 'slot2']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator, assignee=assignee,
            template=template, slots=slots, slot_order=slot_order)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        initial_expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': slot_order,
            'slots': slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        initial_result = resp.content
        self.assertEquals(initial_result, initial_expected)

        new_slot_order = None
        resp = client.execute('request', 'update', data={'slot_order': new_slot_order},
            subject=request_id)

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slot_order': None,
            'slots': slots,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        result = resp.content
        self.assertEquals(result, expected)


    def test_update_slot_order_invalid(self, client):
        """Test update an invalid slot_order"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'}
        }
        slot_order = ['slot1', 'slot2']
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator, assignee=assignee,
            template=template, slots=slots, slot_order=slot_order)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        new_slot_order = ['slot1']
        with self.assertRaisesRegexp(InvalidError, 'invalid-slot-order'):
            client.execute('request', 'update', data={'slot_order': new_slot_order},
                subject=request_id)

    def test_complete_with_products(self, client):
        """Test completing request with products"""
        name = 'test request slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'}
        }
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template, slots=slots)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = self.config.docket_entity.execute('docket.entity/1.0/enamel/1.0/infoset', 'query')
        self.assertEquals(resp.status, 'OK')
        infoset = resp.content['resources'][0]
        infoset_id = infoset['id']

        data = {
            'entities': {
                'slot1': infoset_id,
            },
            'status': 'completed',
        }
        client.execute('request', 'update', subject=request_id, data=data)

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {
                'slot1': {
                    'title': 'Slot 1',
                    'product': surrogate.construct('enamel.surrogates.infoset',
                        infoset)
                },
            },
            'slot_order': None,
            'slots': slots,
            'status': 'completed',
            'template': template,
            'creator': None,
            'claimed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template']})
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        self.assertEquals(result, expected)

    def test_complete_with_products_text_slot(self, client):
        """Test completing request with text slot products"""
        name = 'test request slot with text slot'
        template = 'test request slot template'
        slots = {
            'slot1': {'title': 'Slot 1', 'slot': 'enamel.surrogates.infoset'},
            'slot2': {'title': 'Slot 2', 'slot': 'enamel.surrogates.infoset'},
            'slot3': {'title': 'Slot 3', 'slot': 'text'}
        }
        slot_order = ['slot1', 'slot2', 'slot3',]
        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(client, name=name, originator=originator,
            assignee=assignee, template=template, slots=slots, slot_order=slot_order)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = self.config.docket_entity.execute('docket.entity/1.0/enamel/1.0/infoset', 'query')
        self.assertEquals(resp.status, 'OK')
        infoset = resp.content['resources'][0]
        infoset_id = infoset['id']

        data = {
            'entities': {
                'slot1': infoset_id,
                'slot2': infoset_id,
                'slot3': 'some text',
            },
            'status': 'completed',
        }
        client.execute('request', 'update', subject=request_id, data=data)

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {
                'slot1': {
                    'title': 'Slot 1',
                    'product': surrogate.construct('enamel.surrogates.infoset',
                        infoset)
                },
                'slot2': {
                    'title': 'Slot 2',
                    'product': surrogate.construct('enamel.surrogates.infoset',
                        infoset)
                },
                'slot3': {
                    'title': 'Slot 3',
                    'product': surrogate.construct(
                        schema=fields.Structure({'value': fields.Text()}),
                        value={'value': 'some text'}),
                },
            },
            'slot_order': slot_order,
            'slots': slots,
            'status': 'completed',
            'template': template,
            'creator': None,
            'claimed': None,
            'form': {
                'layout': [
                    {
                        'elements': [
                            {
                                'field': 'slot1',
                                'label': 'Slot 1',
                                'type': 'gridselector',
                            },
                            {
                                'field': 'slot2',
                                'label': 'Slot 2',
                                'type': 'gridselector',
                            },
                            {
                                'field': 'slot3',
                                'label': 'Slot 3',
                                'type': 'textbox',
                            }
                        ]
                    },
                ],
                'schema': fields.Structure(structure={
                    'slot1': fields.UUID(name='slot1', nonempty=True,
                        source={'resource': 'docket.entity/1.0/enamel/1.0/infoset'}),
                    'slot2': fields.UUID(name='slot2', nonempty=True,
                        source={'resource': 'docket.entity/1.0/enamel/1.0/infoset'}),
                    'slot3': fields.Text(name='slot3'),
                })
            }
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['form', 'template']})
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))
        result_schema = result['form'].pop('schema').describe()
        expected_schema  = expected['form'].pop('schema').describe()
        self.assertEquals(result_schema, expected_schema)
        self.assertEquals(result, expected)


class RequestMessageTest(BaseTestCase):
    """Request message test cases"""

    def _assert_messages(self, expected_messages, result_messages):
        self.assertEquals(
            [
                {k: v for k, v in msg.iteritems() if k in ('author', 'message')}
                for msg in result_messages
            ],
            expected_messages
        )
        for msg in result_messages:
            self.assertTrue(isinstance(msg.get('id'), basestring))
            self.assertTrue(isinstance(msg.get('occurrence'), datetime))


    def test_create_message(self, client):
        """Tests new message on request create"""
        name = 'test create message request'
        template = 'test create message request template'

        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        message = {
            'author': originator,
            'message': 'Here\'s a test message',
        }
        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template,
            message=message)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template', 'messages',]})
        self.assertEquals(resp.status, 'OK')
        result = resp.content

        result_messages = result.pop('messages', None) or []
        expected_messages = [message]
        self._assert_messages(expected_messages, result_messages)

        self.assertEquals(result, expected)

    def test_update_message(self, client):
        """Tests new message on request update"""
        name = 'test update message request'
        template = 'test update message request template'

        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        # create message on update
        message = {
            'author': originator,
            'message': 'Here\'s a test message on update',
        }
        resp = client.execute(
            'request', 'update',
            subject=request_id, data={'message': message}
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template', 'messages',]})
        self.assertEquals(resp.status, 'OK')
        result = resp.content

        result_messages = result.pop('messages', None) or []
        expected_messages = [message]
        self._assert_messages(expected_messages, result_messages)

        self.assertEquals(result, expected)

    def test_append_multiple_messages(self, client):
        """Tests appending new message on request update"""
        name = 'test append multiple message request'
        template = 'test append multiple message request template'

        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        messages = [
            {'author': originator, 'message': 'Original message'},
            {'author': assignee, 'message': 'New message'},
        ]
        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template,
            message=messages[0])
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        # append second message on update
        resp = client.execute(
            'request', 'update',
            subject=request_id, data={'message': messages[1]}
        )
        self.assertEquals(resp.status, 'OK')

        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'pending',
            'template': template,
            'creator': None,
            'claimed': None,
            'completed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template', 'messages',]})
        self.assertEquals(resp.status, 'OK')
        result = resp.content

        result_messages = result.pop('messages', None) or []
        self._assert_messages(messages, result_messages)

        self.assertEquals(result, expected)

    def test_require_message_on_request_decline(self, client):
        """Tests require a message on setting status to declined"""
        name = 'test require message on declining request'
        template = 'test require message on declining request template'

        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        # update with no message
        with self.assertRaisesRegexp(InvalidError, 'message-required-for-status'):
            client.execute(
                'request', 'update', subject=request_id,
                data={'status': 'declined'}
            )

        # update with message and invalid author
        message_invalid_author = {
            'author': originator,
            'message': 'Declined status message',
        }
        with self.assertRaisesRegexp(InvalidError, 'invalid-message-author'):
            client.execute(
                'request', 'update', subject=request_id,
                data={'status': 'declined', 'message': message_invalid_author}
            )

        # update with message and valid author
        message_valid_author = {
            'author': assignee,
            'message': 'Declined status message',
        }
        resp = client.execute(
            'request', 'update', subject=request_id,
            data={'status': 'declined', 'message': message_valid_author}
        )
        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'declined',
            'template': template,
            'creator': None,
            'claimed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template', 'messages',]})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))

        result_messages = result.pop('messages', None) or []
        expected_messages = [message_valid_author]
        self._assert_messages(expected_messages, result_messages)

        self.assertEquals(result, expected)

    def test_update_request_message_on_complete(self, client):
        """Tests adding message on setting status to completed"""
        name = 'test new message on completing request'
        template = 'test new message on completing request template'

        resp = self._setup_user(name='originator', email='originator@localhost.local')
        originator = resp.content['id']

        resp = self._setup_user(name='assignee', email='assignee@localhost.local')
        assignee = resp.content['id']

        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        # update with message and invalid author
        message_invalid_author = {
            'author': originator,
            'message': 'Completed status message',
        }
        with self.assertRaisesRegexp(InvalidError, 'invalid-message-author'):
            client.execute(
                'request', 'update', subject=request_id,
                data={'status': 'completed', 'message': message_invalid_author}
            )

        # update with message and valid author
        message_valid_author = {
            'author': assignee,
            'message': 'Completed status message',
        }
        resp = client.execute(
            'request', 'update', subject=request_id,
            data={'status': 'completed', 'message': message_valid_author}
        )
        expected = {
            'assignee': assignee,
            'attachments': [],
            'id': request_id,
            'name': name,
            'originator': originator,
            'products': {},
            'slots': {},
            'slot_order': None,
            'status': 'completed',
            'template': template,
            'creator': None,
            'claimed': None,
        }
        resp = client.execute('request', 'get', subject=request_id,
            data={'include': ['template', 'messages',]})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertTrue(isinstance(result.pop('completed', None), datetime))

        result_messages = result.pop('messages', None) or []
        expected_messages = [message_valid_author]
        self._assert_messages(expected_messages, result_messages)

        self.assertEquals(result, expected)


class RequestTerminalStatus(BaseTestCase):
    """Test cases for requests in a terminal status. Status include the
    following: `canceled`, `completed`, `declined`"""
    def test_update_on_canceled_request(self, client):
        name = 'test update on canceled request'
        template = 'test update on canceled request templated'
        resp = self._setup_user(
            name='originator',
            email='originator@localhost.local'
        )
        originator = resp.content['id']

        resp = self._setup_user(
            name='assignee',
            email='assignee@localhost.local'
        )
        assignee = resp.content['id']

        request_id = self._setup_request_and_change_status(
            client, name, template, 'canceled',
            originator=originator, assignee=assignee)

        with self.assertRaisesRegexp(
                InvalidError, 'cannot-update-with-status'):
            client.execute(
                'request', 'update',
                subject=request_id, data={'name': 'new name'}
            )

    def test_update_on_completed_request(self, client):
        name = 'test update on completed request'
        template = 'test update on completed request templated'
        resp = self._setup_user(
            name='originator',
            email='originator@localhost.local'
        )
        originator = resp.content['id']

        resp = self._setup_user(
            name='assignee',
            email='assignee@localhost.local'
        )
        assignee = resp.content['id']

        request_id = self._setup_request_and_change_status(
            client, name, template, 'completed',
            originator=originator, assignee=assignee)

        with self.assertRaisesRegexp(
                InvalidError, 'cannot-update-with-status'):
            client.execute(
                'request', 'update',
                subject=request_id, data={'name': 'new name'}
            )

    def test_update_on_declined_request(self, client):
        name = 'test update on declined request'
        template = 'test update on declined request templated'
        resp = self._setup_user(
            name='originator',
            email='originator@localhost.local'
        )
        originator = resp.content['id']

        resp = self._setup_user(
            name='assignee',
            email='assignee@localhost.local'
        )
        assignee = resp.content['id']

        resp = self._setup_request(
            client, name=name, originator=originator,
            assignee=assignee, template=template)
        self.assertEquals(resp.status, 'OK')
        request_id = resp.content['id']

        resp = client.execute(
            'request', 'update',
            subject=request_id, data={
                'status': 'declined',
                'message': {
                    'author': assignee,
                    'message': 'Declined status message'
                },
            }
        )
        self.assertEquals(resp.status, 'OK')

        with self.assertRaisesRegexp(
                InvalidError, 'cannot-update-with-status'):
            client.execute(
                'request', 'update',
                subject=request_id, data={'name': 'new name'}
            )
