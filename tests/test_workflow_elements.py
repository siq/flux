import json

from scheme.fields import Structure, Text
from mesh.exceptions import OperationError
from mesh.testing import MeshTestCase
from spire.core import adhoc_configure, Unit
from spire.mesh import MeshDependency
from spire.schema import SchemaDependency

from flux.bundles import API
from flux.engine.parameter import Parameter
from flux.engine.rule import RuleList
from flux.models import Run, Workflow
from nose import SkipTest


adhoc_configure({
    'schema:flux': {
        'url': 'postgresql://postgres@localhost/flux',
    },
    'mesh:docket': {
        'url': 'http://localhost:9996/',
        'specification': 'enamel.bindings.docket.specification',
    },
    'mesh:docket.entity': {
        'url': 'http://localhost:9996/',
        'introspect': True,
    },
    'mesh:platoon': {
        'url': 'http://localhost:9998/',
        'specification': 'enamel.bindings.platoon.specification',
    },
    'mesh:flux': {
        'url': 'http://localhost:9999/',
        'bundle': 'flux.API',
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
        model_instances = [
            (self._runs, Run),
            (self._workflows, Workflow),
        ]

        for instances, model in model_instances:
            for instance in instances:
                try:
                    session.delete(session.query(model).with_lockmode('update').get(instance))
                except:
                    continue
        session.commit()


class TestParamsSpecification(BaseTestCase):
    def test_parse_valid_params(self, client):
        """Tests verification of valid parameters"""
        specification = '\n'.join([
            'schema:',
            '  fieldtype: structure',
            '  structure:',
            '    test_field1:',
            '      fieldtype: text',
            '      required: true',
            'layout:',
            '  - title: Test Section 1',
            '    elements:',
            '      - type: textbox',
            '        field: test_field1',
            '        label: Test Field #1',
            '        options:',
            '          multiline: true',
        ])
        parameters = Parameter.unserialize(specification)
        parameters.verify()

    def test_missing_schema_field(self, client):
        """Tests failure when schema field is missing"""
        specification = '\n'.join([
            'schema:',
            '  fieldtype: structure',
            '  structure:',
            '    test_field1:',
            '      fieldtype: text',
            '      required: true',
            '    test_field2:',
            '      fieldtype: integer',
            '      required: true',
            'layout:',
            '  - title: Test Section 1',
            '    elements:',
            '      - type: textbox',
            '        field: test_field1',
            '        label: Test Field #1',
            '        options:',
            '          multiline: true',
            '      - type: textbox',
            '        field: test_field2',
            '        label: Test Field #2',
            '      - type: checkbox',
            '        field: test_field3',
            '        label: Test Field #3',
        ])
        parameters = Parameter.unserialize(specification)
        with self.assertRaises(OperationError):
            parameters.verify()

class TestSpecification(BaseTestCase):
    def test_workflow_verify_rulelist_pass(self, client):
        """Tests verification of valid rulelist"""
        steps = {
            'step-1': None,
            'step-2': None,
            'step-3': None,
        }
        specification = '\n'.join([
            '- actions:',
            '  - action: execute-step',
            '    step: step-1',
            '  - action: execute-step',
            '    step: step-2',
            '  - action: execute-operation',
            '    operation: flux:test-operation',
            '  condition: some condition',
            '- actions:',
            '  - action: execute-step',
            '    step: step-3',
        ])
        rulelist = RuleList.unserialize(specification)
        rulelist.verify(steps)

    def test_workflow_verify_rulelist_fail(self, client):
        """Tests rule lists with invalid step operations"""
        steps = {
            'step-1': None,
            'step-2': None,
        }
        specification = '\n'.join([
            '- actions:',
            '  - action: execute-step',
            '    step: step-1',
            '  - action: execute-step',
            '    step: step-3',
            '  - action: execute-operation',
            '    operation: flux:test-operation',
            '  condition: some condition',
            '- actions:',
            '  - action: execute-step',
            '    step: step-2',
        ])
        rulelist = RuleList.unserialize(specification)
        with self.assertRaises(OperationError):
            rulelist.verify(steps)

    def test_workflow_verify_specification_pass(self, client):
        """Tests valid specification workflow yaml"""
        name = 'valid specification workflow'
        specification = '\n'.join([
            'name: %s' % name,
            'parameters:',
            '  schema:',
            '    fieldtype: structure',
            '    structure:',
            '      some_test_arg:',
            '        fieldtype: text',
            '        required: true',
            '  layout:',
            '    - title: Test Section 1',
            '      elements:',
            '        - type: textbox',
            '          field: some_test_arg',
            '          label: Test Field #1',
            '          options:',
            '            multiline: true',
            'entry: step-0',
            'steps: ',
            '  step-0:',
            '    operation: flux:test-operation',
            '    timeout: 30',
            '    preoperation:',
            '     - actions:',
            '       - action: execute-step',
            '         step: step-1',
            '         parameters:',
            '           arg1: ${some_test_arg}',
            '           arg2: literal arg',
            '    postoperation:',
            '     - actions:',
            '       - action: execute-operation',
            '         operation: flux:test-operation',
            '       condition: some condition',
            '       terminal: false',
            '  step-1:',
            '     operation: flux:test-operation',
        ])
        Workflow._verify_specification(specification)

    def test_workflow_verify_specification_fail(self, client):
        """Tests invalid specification workflow yaml"""
        name = 'invalid specification workflow'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: non-existing-step',
            'steps: ',
            '  step-0:',
            '    operation: flux:test-operation',
            '    postoperation:',
            '     - actions:',
            '       - action: execute-operation',
            '         operation: flux:test-operation',
            '       condition: some condition',
            '       terminal: false',
        ])
        with self.assertRaises(OperationError):
            Workflow._verify_specification(specification)
