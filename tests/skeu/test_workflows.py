from datetime import datetime
from time import sleep

from spire.core import adhoc_configure, Unit
from spire.schema import SchemaDependency
from mesh.testing import MeshTestCase
from mesh.exceptions import GoneError, InvalidError, OperationError

from flux.bundles import API
from flux.engine.rule import RuleList
from flux.models import Workflow, Run


adhoc_configure({
    'schema:flux': {
        'url': 'postgresql://postgres@localhost/flux'
    },
    'mesh:flux': {
        'url': 'http://localhost:9995/',
        'bundle': 'flux.API',
    },
    'mesh:docket': {
        'url': 'http://localhost:9996/',
        'specification': 'flux.bindings.docket.specification',
    },
    'mesh:platoon': {
        'url': 'http://localhost:9998/',
        'specification': 'flux.bindings.platoon.specification',
    },
    'mesh:truss': {
        'url': 'http://localhost:9997/',
        'specification': 'flux.bindings.truss.specification',
    },
})


class TestDependency(Unit):
    schema = SchemaDependency('flux')


class BaseTestCase(MeshTestCase):
    bundle = API
    maxDiff = None
    config = TestDependency()

    def setUp(self):
        self._workflows = []
        self._runs = []

    def tearDown(self):
        session = self.config.schema.session
        model_instances = (
            (Run, self._runs),
            (Workflow, self._workflows),
        )
        for model, instances in model_instances:
            for instance in instances:
                try:
                    session.delete(session.query(model).with_lockmode('update').get(instance))
                    session.commit()
                except:
                    session.rollback()
                    continue


class TestWorkflow(BaseTestCase):
    """General Workflow test cases."""
    def _setup_workflow(self, client, name, specification=None):
        if specification is None:
            specification = '\n'.join([
                'name: %s' % name,
                'entry: step-0',
                'steps:',
                ' step-0:',
                '  operation: flux:test-operation',
            ])
        self._workflow_spec = specification
        data={'name': name, 'specification': specification}
        resp = client.execute('workflow', 'create', None, data=data)
        try:
            workflow_id = resp.content['id']
        except (AttributeError, KeyError):
            pass
        else:
            self._workflows.append(workflow_id)
        return resp

    def test_create_workflow(self, client):
        """Tests creating and fetching a workflow resource"""
        resp = self._setup_workflow(client, 'test create workflow')
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        expected = {
            'name': u'test create workflow',
            'designation': None,
            'specification': unicode(self._workflow_spec),
            'is_service': False,
            'type': 'yaml',
        }

        resp = client.execute(
                'workflow', 'get', workflow_id,
                {'include': ['specification']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content

        result.pop('id')
        self.assertTrue(isinstance(result.pop('modified'), datetime))

        self.assertEquals(result, expected)

    def test_workflow_empty_form(self, client):
        """Tests creating and fetching a workflow resource with an empty form"""
        name = 'test workflow empty form'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: flux:test-operation',
        ])
        resp = self._setup_workflow(client, name, specification=specification)
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        expected = {
            'name': u'test workflow empty form',
            'form': None,
            'designation': None,
            'is_service': False,
            'specification': unicode(self._workflow_spec),
            'type': 'yaml',
        }

        resp = client.execute(
                'workflow', 'get', workflow_id,
                {'include': ['specification', 'form']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content

        result.pop('id')
        self.assertTrue(isinstance(result.pop('modified'), datetime))

        self.assertEquals(result, expected)

    def test_workflow_form(self, client):
        """Tests creating and fetching a workflow resource with an form"""
        name = 'test workflow form'
        specification = '\n'.join([
            'name: %s' % name,
            'schema:',
            '  fieldtype: structure',
            '  structure:',
            '    test_field_1:',
            '      fieldtype: text',
            '      required: true',
            'layout:',
            '  - title: Test Section 1',
            '    elements:',
            '      - type: textbox',
            '        field: test_field_1',
            '        label: Test Field 1',
            '        options:',
            '            multiline: true',
            'entry: step-0',
            'steps:',
            '   step-0:',
            '     operation: flux:test-operation',
        ])
        resp = self._setup_workflow(client, name, specification=specification)
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        expected_schema = {
            '__type__': 'structure',
            'structural': True,
            'structure': {
                u'test_field_1': {
                    '__type__': 'text',
                    'name': u'test_field_1',
                    'required': True,
                },
            }
        }
        expected = {
            'name': u'test workflow form',
            'form': {
                'layout': [
                    {
                        'title': u'Test Section 1',
                        'elements': [{
                            'type': u'textbox',
                            'field': u'test_field_1',
                            'label': u'Test Field 1',
                            'options': {'multiline': True},
                        }],
                    },
                ],
            },
            'designation': None,
            'is_service': False,
            'specification': unicode(self._workflow_spec),
            'type': 'yaml',
        }

        resp = client.execute(
                'workflow', 'get', workflow_id,
                {'include': ['specification', 'form']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content

        result.pop('id')
        self.assertTrue(isinstance(result.pop('modified'), datetime))
        actual_schema = result['form'].pop('schema').describe()

        self.assertEqual(actual_schema, expected_schema)
        self.assertEquals(result, expected)

    def test_update_workflow(self, client):
        """Tests updating of workflow resource"""
        resp = self._setup_workflow(client, 'test update workflow')
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        resp = client.execute(
                'workflow', 'get', workflow_id,
                {'include': ['specification', 'form']})
        self.assertEquals(resp.status, 'OK')
        original_vals = {k: resp.content.pop(k) for k in ('name', 'modified',)}

        sleep(3)
        new_name = 'updated test update workflow'
        resp = client.execute('workflow', 'update', workflow_id, {'name': new_name})
        self.assertEquals(resp.status, 'OK')

        resp = client.execute(
                'workflow', 'get', workflow_id,
                {'include': ['specification', 'form']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        for k in ('name', 'modified'):
            self.assertNotEquals(original_vals[k], result[k])

        self.assertEquals(result['name'], new_name)

    def test_delete_workflow(self, client):
        """Tests deletion of workflow resource"""
        resp = self._setup_workflow(client, 'test delete workflow')
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        resp = client.execute(
                'workflow', 'get', workflow_id,
                {'include': ['specification', 'form']})
        self.assertEquals(resp.status, 'OK')
        result = resp.content
        self.assertEquals(result['id'], workflow_id)

        resp = client.execute('workflow', 'delete', workflow_id)
        self.assertEquals(resp.status, 'OK')

        with self.assertRaises(GoneError):
            client.execute('workflow', 'get', workflow_id)

    def test_duplicate_name_workflow1(self, client):
        """Tests creating a workflow with an existing workflow name"""
        resp = self._setup_workflow(client, 'test duplicate name workflow 1')
        self.assertEquals(resp.status, 'OK')

        with self.assertRaises(InvalidError):
            self._setup_workflow(client, 'test duplicate name workflow 1')

    def test_duplicate_name_workflow2(self, client):
        """Tests updating a workflow with an existing workflow name"""
        duplicate_name = 'test duplicate name workflow 2'
        resp = self._setup_workflow(client, duplicate_name)
        self.assertEquals(resp.status, 'OK')

        resp = self._setup_workflow(client, 'test duplicate name workflow 2 a')
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        with self.assertRaises(InvalidError):
            client.execute('workflow', 'update', workflow_id, {'name': duplicate_name})

    def test_duplicate_name_workflow3(self, client):
        """Tests against false positive when updating a workflow without name change."""
        resp = self._setup_workflow(client, 'test duplicate name workflow 3')
        self.assertEquals(resp.status, 'OK')
        workflow_id = resp.content['id']

        resp = client.execute('workflow', 'update', workflow_id,
                {'name': 'test duplicate name workflow 3'})
        self.assertEquals(resp.status, 'OK')


class TestWorkflowGenerate(BaseTestCase):
    """Tests cases of Workflow's generate method."""
    def test_generate_request(self, client):
        """Simple test of generate request"""
        data = {
            'name': 'test generate request',
            'description': 'test description',
            'operations': [
                {
                    'description': 'operation description',
                    'operation': 'flux:test-operation',
                    'run_params': {'foo': 'bar'},
                }
            ],
        }
        resp = client.execute('workflow', 'generate', data=data)
        self.assertEquals('OK', resp.status)
        result = resp.content

        expected = {
            'name': u'test generate request',
            'description': u'test description',
            'specification': u'\n'.join([
                'name: test generate request',
                'entry: step:0',
                'steps:',
                '  step:0:',
                '    description: operation description',
                '    operation: flux:test-operation',
                '    parameters:',
                '      foo: bar',
            ]),
        }
        self.assertEquals(expected, result)

    def test_generate_multi_operations(self, client):
        """Test generate request with multi-operations"""
        data = {
            'name': 'test generate multi ops',
            'description': 'test description',
            'operations': [
                {
                    'description': 'operation description',
                    'operation': 'flux:test-operation',
                    'run_params': {'foo': 'bar'},
                },
                {
                    'description': 'operation description',
                    'operation': 'flux:test-operation',
                    'run_params': {'foo': 'bar'},
                    'step_params': {'spam': 'eggs'},
                }
            ],
        }
        resp = client.execute('workflow', 'generate', data=data)
        self.assertEquals('OK', resp.status)
        result = resp.content

        expected = {
            'name': u'test generate multi ops',
            'description': u'test description',
            'specification': u'\n'.join([
                'name: test generate multi ops',
                'entry: step:0',
                'steps:',
                '  step:0:',
                '    description: operation description',
                '    operation: flux:test-operation',
                '    parameters:',
                '      foo: bar',
                '    postoperation:',
                '      - actions:',
                '          - action: execute-step',
                '            parameters:',
                '              spam: eggs',
                '            step: step:1',
                '        terminal: false',
                '  step:1:',
                '    description: operation description',
                '    operation: flux:test-operation',
                '    parameters:',
                '      foo: bar',
            ]),
        }
        self.assertEquals(expected, result)
