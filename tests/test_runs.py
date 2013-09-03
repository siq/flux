from datetime import datetime
from nose import SkipTest
from time import sleep

from scheme import current_timestamp, fields
from spire.core import adhoc_configure, Unit
from spire.schema import SchemaDependency
from mesh.testing import MeshTestCase
from mesh.exceptions import GoneError, InvalidError, OperationError

from flux.bundles import API
from flux.engine.rule import RuleList
from flux.models import Operation, Run, Workflow


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
        self._operations = []

    def tearDown(self):
        session = self.config.schema.session
        model_instances = (
            (Run, self._runs),
            (Workflow, self._workflows),
            (Operation, self._operations),
        )
        for model, instances in model_instances:
            for instance in instances:
                try:
                    session.delete(session.query(model).with_lockmode('update').get(instance))
                    session.commit()
                except:
                    session.rollback()
                    continue

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
        data = {'name': name, 'specification': specification}
        resp = client.execute('workflow', 'create', None, data=data)
        try:
            workflow_id = resp.content['id']
        except (AttributeError, KeyError):
            pass
        else:
            self._workflows.append(workflow_id)
        return resp

    def _setup_run(self, client, workflow_id, parameters=None, name=None):
        data = {'workflow_id': workflow_id}
        if name:
            data['name'] = name
        if parameters:
            data['parameters'] = parameters

        resp = client.execute('run', 'create', None, data=data)
        try:
            run_id = resp.content['id']
        except (AttributeError, KeyError):
            pass
        else:
            self._runs.append(run_id)
        return resp


class TestSimpleRunCases(BaseTestCase):
    def test_run_workflow1(self, client):
        """Tests simple workflow run cycle"""
        workflow_name = 'test run workflow 1'
        resp1 = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp1.status)
        workflow_id = resp1.content['id']

        resp2 = self._setup_run(client, workflow_id)
        self.assertEqual('OK', resp2.status)
        run_id = resp2.content['id']

        limit = 15
        wait = 20
        while limit:
            sleep(wait)
            resp = client.execute('run', 'get', run_id)
            self.assertEqual('OK', resp.status)
            result = resp.content
            run_status = result['status']
            if 'pending' == run_status:
                limit -= 1
                continue

            self.assertEquals('completed', run_status)
            self.assertTrue(result.pop('ended') >= result.pop('started'))
            expected = {
                'id': run_id,
                'name': workflow_name,
                'parameters': None,
                'workflow_id': workflow_id,
                'products': {},
                'status': u'completed',
            }
            self.assertEquals(expected, result)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_run_workflow2(self, client):
        """Tests simple workflow run and execution cycle"""
        workflow_name = u'test run workflow 2'
        resp1 = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp1.status)
        workflow_id = resp1.content['id']

        resp2 = self._setup_run(client, workflow_id)
        self.assertEqual('OK', resp2.status)
        run_id = resp2.content['id']

        limit = 15
        wait = 20
        while limit:
            sleep(wait)
            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEqual('OK', resp.status)
            result = resp.content
            run_status = result['status']
            if 'pending' == run_status:
                limit -= 1
                continue

            self.assertEquals('completed', run_status)

            run_ended = result.pop('ended')
            run_started = result.pop('started')

            result['executions'][0].pop('id')
            execution_ended = result['executions'][0].pop('ended')
            execution_started = result['executions'][0].pop('started')

            self.assertTrue(run_ended >= run_started)
            self.assertTrue(execution_ended >= execution_started)
            self.assertTrue(execution_ended >= run_started)
            self.assertTrue(run_ended >= execution_started)

            expected = {
                'id': run_id,
                'name': workflow_name,
                'parameters': None,
                'workflow_id': workflow_id,
                'products': {},
                'status': u'completed',
                'executions': [{
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': u'step-0',
                    'name': u'Test Operation',
                    'status': u'completed',
                }]
            }
            self.assertEquals(expected, result)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_multi_step_run(self, client):
        """Tests for multistep workflow runs"""
        workflow_name = u'test multistep workflow run'
        specification = '\n'.join([
            'name: %s' % workflow_name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: flux:test-operation',
            '  postoperation:',
            '    - actions:',
            '        - action: execute-step',
            '          step: step-1',
            ' step-1:',
            '  operation: flux:test-operation',
            '  postoperation:',
            '    - actions:',
            '        - action: execute-step',
            '          step: step-2',
            ' step-2:',
            '  operation: flux:test-operation',
        ])
        resp1 = self._setup_workflow(client, workflow_name,
                specification=specification)
        self.assertEqual('OK', resp1.status)
        workflow_id = resp1.content['id']

        resp2 = self._setup_run(client, workflow_id)
        self.assertEqual('OK', resp2.status)
        run_id = resp2.content['id']

        limit = 10
        wait = 10
        while limit:
            sleep(wait)
            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEqual('OK', resp.status)
            result = resp.content
            run_status = result['status']
            if 'pending' == run_status:
                limit -= 1
                continue

            self.assertEquals('completed', run_status)

            run_ended = result.pop('ended')
            run_started = result.pop('started')
            self.assertTrue(run_ended >= run_started)

            ancestor_ids = []
            for execution in result['executions']:
                ancestor_ids.append(execution.pop('id'))
                execution_ended = execution.pop('ended')
                execution_started = execution.pop('started')

                self.assertTrue(execution_ended >= execution_started)
                self.assertTrue(execution_ended >= run_started)
                self.assertTrue(run_ended >= execution_started)

            expected = {
                'id': run_id,
                'name': workflow_name,
                'parameters': None,
                'workflow_id': workflow_id,
                'products': {},
                'status': u'completed',
                'executions': [
                    {
                        'execution_id': 1,
                        'ancestor_id': None,
                        'step': u'step-0',
                        'name': u'Test Operation',
                        'status': u'completed',
                    },
                    {
                        'execution_id': 2,
                        'ancestor_id': ancestor_ids[0],
                        'step': u'step-1',
                        'name': u'Test Operation',
                        'status': u'completed',
                    },
                    {
                        'execution_id': 3,
                        'ancestor_id': ancestor_ids[1],
                        'step': u'step-2',
                        'name': u'Test Operation',
                        'status': u'completed',
                    },
                ]
            }
            self.assertEquals(expected, result)
            return


class TestRunOutcomeCases(BaseTestCase):
    """Tests workflow runs interaction with different outcomes"""
    def _setup_operation(self, client, operation_id, outcomes=None, parameters=None):
        if outcomes is None:
            outcomes = {
                'finished': {'outcome': 'success'},
                'failed': {'outcome': 'failure'},
            }
        data = {
            'name': 'Test Operation %s' % operation_id,
            'phase': 'operation',
            'schema': fields.Structure({
                'outcome': fields.Token(default='completed'),
                'duration': fields.Integer(default=5),
            }),
            'outcomes': outcomes,
        }
        if parameters:
            data['parameters'] = parameters
        self._operations.append(operation_id)
        return client.execute('operation', 'put', subject=operation_id, data=data)

    def _setup_active_run(self, workflow_id, steps, parameters=None):
        session = self.config.schema.session
        run = Run.create(session, workflow_id, started=current_timestamp())
        session.commit()
        self._runs.append(run.id)
        execution = None
        for step in steps:
            execution = run.create_execution(session, step,
                    parameters=parameters, ancestor=execution)
            execution.start()
            sleep(1)
        session.commit()
        return run

    def test_success_outcome(self, client):
        '''Test successful run outcome'''
        operation_id = 'fluxtests:success-outcome'
        resp1 = self._setup_operation(client, operation_id)
        self.assertEqual('OK', resp1.status)

        workflow_name = 'test sucess outcome'
        specification = '\n'.join([
            'name: %s' % workflow_name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: %s' % operation_id,
        ])
        resp2 = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp2.status)
        workflow_id = resp2.content['id']

        run = self._setup_active_run(workflow_id, ('step-0',))
        run_id = run.id
        data = {
            'id': run.executions[-1].id,
            'tag': 'step-0',
            'subject': operation_id,
            'status': 'completed',
            'output': {'status': 'valid', 'outcome': 'finished'},
        }
        client.execute('operation', 'process', subject=operation_id, data=data)
        resp3 = client.execute('run', 'get', subject=run_id, data={'include': ['executions']})
        self.assertEquals('OK', resp3.status)
        result = resp3.content

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        execution = result['executions'][-1]
        execution_ended = execution.pop('ended')
        execution_started = execution.pop('started')

        self.assertTrue(run_ended >= run_started)
        self.assertTrue(execution_ended >= execution_started)
        self.assertTrue(execution_ended >= run_started)
        self.assertTrue(run_ended >= execution_started)

        expected = {
            'id': run_id,
            'name': workflow_name,
            'parameters': None,
            'workflow_id': workflow_id,
            'products': {},
            'status': u'completed',
            'executions': [{
                'id': execution['id'],
                'execution_id': 1,
                'ancestor_id': None,
                'step': u'step-0',
                'name': None,
                'status': u'completed',
            }]
        }
        self.assertEquals(expected, result)

    def test_failure_outcome(self, client):
        '''Test failure run outcome'''
        operation_id = 'fluxtests:failure-outcome'
        resp1 = self._setup_operation(client, operation_id)
        self.assertEqual('OK', resp1.status)

        workflow_name = 'test failure outcome'
        specification = '\n'.join([
            'name: %s' % workflow_name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: %s' % operation_id,
        ])
        resp2 = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp2.status)
        workflow_id = resp2.content['id']

        run = self._setup_active_run(workflow_id, ('step-0',))
        run_id = run.id
        data = {
            'id': run.executions[-1].id,
            'tag': 'step-0',
            'subject': operation_id,
            'status': 'completed',
            'output': {'status': 'valid', 'outcome': 'failed'},
        }
        client.execute('operation', 'process', subject=operation_id, data=data)
        resp3 = client.execute('run', 'get', subject=run_id, data={'include': ['executions']})
        self.assertEquals('OK', resp3.status)
        result = resp3.content

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        execution = result['executions'][-1]
        execution_ended = execution.pop('ended')
        execution_started = execution.pop('started')

        self.assertTrue(run_ended >= run_started)
        self.assertTrue(execution_ended >= execution_started)
        self.assertTrue(execution_ended >= run_started)
        self.assertTrue(run_ended >= execution_started)

        expected = {
            'id': run_id,
            'name': workflow_name,
            'parameters': None,
            'workflow_id': workflow_id,
            'products': {},
            'status': u'failed',
            'executions': [{
                'id': execution['id'],
                'execution_id': 1,
                'ancestor_id': None,
                'step': u'step-0',
                'name': None,
                'status': u'failed',
            }]
        }
        self.assertEquals(expected, result)

    def test_invalidated_run(self, client):
        '''Test invalidated run outcome'''
        operation_id = 'fluxtests:invalid_run'
        resp1 = self._setup_operation(client, operation_id)
        self.assertEqual('OK', resp1.status)

        workflow_name = 'test invalid run'
        specification = '\n'.join([
            'name: %s' % workflow_name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: %s' % operation_id,
        ])
        resp2 = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp2.status)
        workflow_id = resp2.content['id']

        run = self._setup_active_run(workflow_id, ('step-0',))
        run_id = run.id
        data = {
            'id': run.executions[-1].id,
            'tag': 'step-0',
            'subject': operation_id,
            'status': 'completed',
            'output': {'status': 'invalid', 'errors': None},
        }
        client.execute('operation', 'process', subject=operation_id, data=data)
        resp3 = client.execute('run', 'get', subject=run_id, data={'include': ['executions']})
        self.assertEquals('OK', resp3.status)
        result = resp3.content

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        execution = result['executions'][-1]
        execution_ended = execution.pop('ended')
        execution_started = execution.pop('started')

        self.assertTrue(run_ended >= run_started)
        self.assertTrue(execution_ended >= execution_started)
        self.assertTrue(execution_ended >= run_started)
        self.assertTrue(run_ended >= execution_started)

        expected = {
            'id': run_id,
            'name': workflow_name,
            'parameters': None,
            'workflow_id': workflow_id,
            'products': {},
            'status': u'invalidated',
            'executions': [{
                'id': execution['id'],
                'execution_id': 1,
                'ancestor_id': None,
                'step': u'step-0',
                'name': None,
                'status': u'invalidated',
            }]
        }
        self.assertEquals(expected, result)

    def test_abort_run(self, client):
        '''Test setting run status to aborted'''
        operation_id = 'fluxtests:test-operation'
        workflow_name = 'test abort run'
        specification = '\n'.join([
            'name: %s' % workflow_name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: %s' % operation_id,
            ' step-1:',
            '  operation: %s' % operation_id,
        ])
        resp2 = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp2.status)
        workflow_id = resp2.content['id']

        run = self._setup_active_run(workflow_id, ('step-0','step-1'))
        run_id = run.id
        client.execute('run', 'update', subject=run_id, data={'status': 'aborted'})


        limit = 10
        wait = 5
        while limit:
            sleep(wait)
            resp = client.execute('run', 'get', subject=run_id, data={'include': ['executions']})
            self.assertEquals('OK', resp.status)
            result = resp.content
            run_status = result['status']
            if 'pending' == run_status:
                limit -= 1
                continue

            run_ended = result.pop('ended')
            run_started = result.pop('started')
            self.assertTrue(run_ended >= run_started)

            ancestor_ids = []
            for execution in result['executions']:
                ancestor_ids.append(execution.pop('id'))
                execution_ended = execution.pop('ended')
                execution_started = execution.pop('started')

                self.assertTrue(execution_ended >= execution_started)
                self.assertTrue(execution_ended >= run_started)
                self.assertTrue(run_ended >= execution_started)

            expected = {
                'id': run_id,
                'name': workflow_name,
                'parameters': None,
                'workflow_id': workflow_id,
                'products': {},
                'status': u'aborted',
                'executions': [
                    {
                        'execution_id': 1,
                        'ancestor_id': None,
                        'step': u'step-0',
                        'name': None,
                        'status': u'aborted',
                    },
                    {
                        'execution_id': 2,
                        'ancestor_id': ancestor_ids[0],
                        'step': u'step-1',
                        'name': None,
                        'status': u'aborted',
                    },
                ],
            }
            self.assertEquals(expected, result)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_abort_execution(self, client):
        '''Test setting execution status to aborted'''
        operation_id = 'fluxtests:test-operation'
        workflow_name = 'test abort execution'
        specification = '\n'.join([
            'name: %s' % workflow_name,
            'entry: step-0',
            'steps:',
            ' step-0:',
            '  operation: %s' % operation_id,
            ' step-1:',
            '  operation: %s' % operation_id,
        ])
        resp2 = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp2.status)
        workflow_id = resp2.content['id']

        run = self._setup_active_run(workflow_id, ('step-0','step-1'))
        run_id = run.id
        execution_id = run.executions[-1].id
        client.execute('execution', 'update', subject=execution_id, data={'status': 'aborted'})

        limit = 10
        wait = 5
        while limit:
            sleep(wait)
            resp = client.execute('run', 'get', subject=run_id, data={'include': ['executions']})
            self.assertEquals('OK', resp.status)
            result = resp.content
            run_status = result['status']
            if 'pending' == run_status:
                limit -= 1
                continue

            run_ended = result.pop('ended')
            run_started = result.pop('started')
            self.assertTrue(run_ended >= run_started)

            ancestor_ids = []
            for execution in result['executions']:
                ancestor_ids.append(execution.pop('id'))
                execution_ended = execution.pop('ended')
                execution_started = execution.pop('started')

                self.assertTrue(execution_ended >= execution_started)
                self.assertTrue(execution_ended >= run_started)
                self.assertTrue(run_ended >= execution_started)

            expected = {
                'id': run_id,
                'name': workflow_name,
                'parameters': None,
                'workflow_id': workflow_id,
                'products': {},
                'status': u'aborted',
                'executions': [
                    {
                        'execution_id': 1,
                        'ancestor_id': None,
                        'step': u'step-0',
                        'name': None,
                        'status': u'aborted',
                    },
                    {
                        'execution_id': 2,
                        'ancestor_id': ancestor_ids[0],
                        'step': u'step-1',
                        'name': None,
                        'status': u'aborted',
                    },
                ],
            }
            self.assertEquals(expected, result)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_success_outcome_with_concurrent_executions(self, client):
        '''Test success run outcome with active concurrent executions'''
        raise SkipTest

    def test_failure_outcome_with_concurrent_executions(self, client):
        '''Test failure run outcome with active concurrent executions'''
        raise SkipTest

    def test_invalidated_outcome_with_concurrent_executions(self, client):
        '''Test invalidated run outcome with active concurrent executions'''
        raise SkipTest

    def test_timedout_run(self, client):
        '''Test timedout run'''
        raise SkipTest

    def test_timedout_run_with_concurrent_executions(self, client):
        '''Test timedout run with active concurrent executions'''
        raise SkipTest

class TestIgnoreStatusRuns(BaseTestCase):
    def test_failure(self, client):
        """Test failure run with failed step."""
        name = u'test failure'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description : test failed operation',
            '    parameters:',
            '      outcome: failed',
            '    postoperation:',
            '      - actions:',
            '          - action: execute-step',
            '            step: step:1',
            '            parameters:',
            '              outcome: completed',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description : test completed operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 10
        limit = 10
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'failed',
                'parameters': None,
                'products': {},
                'executions': [{
                    'execution_id': 1,
                    'step': u'step:0',
                    'name': u'test failed operation',
                    'status': u'failed',
                }],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_ignore_failure(self, client):
        """Test use of ignore failure of failed step."""
        name = u'test ignore failure'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description: test failed operation',
            '    parameters:',
            '      outcome: failed',
            '    postoperation:',
            '      - actions:',
            '          - action: ignore-step-failure',
            '          - action: execute-step',
            '            parameters:',
            '              outcome: completed',
            '            step: step:1',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description: test operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 20
        limit = 15
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'failed',
                'parameters': None,
                'products': {},
                'executions': [
                    {
                        'execution_id': 1,
                        'step': u'step:0',
                        'name': u'test failed operation',
                        'status': u'failed',
                    },
                    {
                        'execution_id': 2,
                        'step': u'step:1',
                        'name': u'test operation',
                        'status': u'completed',
                    },
                ],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_ignore_failure_incorrect_use(self, client):
        """Test failure with ignore step with incorrect use case."""
        name = u'test ignore failure bad case'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description : test failed operation',
            '    parameters:',
            '      outcome: failed',
            '    postoperation:',
            '      - actions:',
            '          - action: execute-step',
            '            step: step:1',
            '            parameters:',
            '              outcome: completed',
            '          - action: ignore-step-failure',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description : test completed operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 20
        limit = 15
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'failed',
                'parameters': None,
                'products': {},
                'executions': [{
                    'execution_id': 1,
                    'step': u'step:0',
                    'name': u'test failed operation',
                    'status': u'failed',
                }],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

class TestRunTimedoutCases(BaseTestCase):
    """Test run cases involving the timedout status."""
    def test_timedout_case(self, client):
        """Test timedout with multi-step run."""
        name = u'test timedout run'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description : test timedout operation',
            '    timeout: 1',
            '    parameters:',
            '      duration: 100',
            '    postoperation:',
            '      - actions:',
            '          - action: execute-step',
            '            step: step:1',
            '            parameters:',
            '              outcome: completed',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description : test completed operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 20
        limit = 15
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'timedout',
                'parameters': None,
                'products': {},
                'executions': [
                    {
                        'execution_id': 1,
                        'step': u'step:0',
                        'name': u'test timedout operation',
                        'status': u'timedout',
                    },
                ],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_ignore_timedout_case(self, client):
        """Test ignore-failure on timedout step."""
        name = u'test ignore timedout run'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description : test timedout operation',
            '    timeout: 1',
            '    parameters:',
            '      duration: 100',
            '    postoperation:',
            '      - actions:',
            '          - action: ignore-step-failure',
            '          - action: execute-step',
            '            step: step:1',
            '            parameters:',
            '              outcome: completed',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description : test completed operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 20
        limit = 15
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'timedout',
                'parameters': None,
                'products': {},
                'executions': [
                    {
                        'execution_id': 1,
                        'step': u'step:0',
                        'name': u'test timedout operation',
                        'status': u'timedout',
                    },
                    {
                        'execution_id': 2,
                        'step': u'step:1',
                        'name': u'test completed operation',
                        'status': u'completed',
                    },
                ],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

class TestInvalidRunCase(BaseTestCase):
    """Test run cases involving invalidated status."""
    def test_invalidated_case(self, client):
        """Test invalidated run with multi-step run."""
        name = u'test invalidated run'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description : test invalid operation',
            '    parameters:',
            '      outcome: invalidated',
            '    postoperation:',
            '      - actions:',
            '          - action: execute-step',
            '            step: step:1',
            '            parameters:',
            '              outcome: completed',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description : test completed operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 20
        limit = 15
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'invalidated',
                'parameters': None,
                'products': {},
                'executions': [
                    {
                        'execution_id': 1,
                        'step': u'step:0',
                        'name': u'test invalid operation',
                        'status': u'invalidated',
                    },
                ],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

    def test_ignore_invalidated_case(self, client):
        name = u'test ignore invalidated run'
        specification = '\n'.join([
            'name: %s' % name,
            'entry: step:0',
            'steps:',
            '  step:0:',
            '    operation: flux:test-operation',
            '    description : test invalid operation',
            '    parameters:',
            '      outcome: invalidated',
            '    postoperation:',
            '      - actions:',
            '          - action: ignore-step-failure',
            '          - action: execute-step',
            '            step: step:1',
            '            parameters:',
            '              outcome: completed',
            '        terminal: false',
            '  step:1:',
            '    operation: flux:test-operation',
            '    description : test completed operation',
            '    parameters:',
            '      outcome: completed',
        ])
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        wait = 20
        limit = 15
        for i in range(10):
            sleep(wait)

            resp = client.execute('run', 'get', run_id, {'include': ['executions']})
            self.assertEquals('OK', resp.status)

            run = resp.content

            if run['status'] == 'pending':
                continue

            result = run
            run_started = result.pop('started')
            run_ended = result.pop('ended')
            self.assertTrue(run_ended >= run_started)

            for execution in result['executions']:
                execution.pop('id')
                execution.pop('ancestor_id')
                exec_started = execution.pop('started')
                exec_ended = execution.pop('ended')

                self.assertTrue(exec_ended >= exec_started)
                self.assertTrue(run_ended >= exec_ended)
                self.assertTrue(exec_started >= run_started)

            expected = {
                'id': run_id,
                'name': name,
                'workflow_id': workflow_id,
                'status': u'invalidated',
                'parameters': None,
                'products': {},
                'executions': [
                    {
                        'execution_id': 1,
                        'step': u'step:0',
                        'name': u'test invalid operation',
                        'status': u'invalidated',
                    },
                ],
            }
            self.assertEquals(result, expected)
            break
        else:
            raise Exception('Run \'%s\' not completing' % run_id)

