from time import sleep

from scheme import fields, Yaml
from spire.core import adhoc_configure, Unit
from spire.schema import SchemaDependency
from mesh.testing import MeshTestCase
from mesh.exceptions import InvalidError 

from flux.bundles import API
from flux.models import Operation, Run, Workflow


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
    'mesh:platoon': {
        'url': 'http://localhost:4321/',
        'specification': 'flux.bindings.platoon.specification',
    },
    'mesh:truss': {
        'url': 'http://localhost:9999/api',
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

    def _poll_run_status(self, client, run_id, status, include=None, limit=5, wait=6):
        run = None
        data = {'include': include} if include else None
        while limit:
            resp = client.execute('run', 'get', run_id, data=data)
            self.assertEqual('OK', resp.status)
            run = resp.content
            if run['status'] == status:
                break
            limit -= 1
            limit and sleep(wait)
        else:
            raise Exception(
                'Status of Run(id=%s, status=%s) not updating to %s' % (
                    run_id, run['status'], status))

        return run

    def _setup_active_run(self, client, workflow_id,
            steps=None, parameters=None, limit=5, wait=6):
        data = {'workflow_id': workflow_id, 'parameters': parameters}
        resp = client.execute('run', 'create', data=data)
        self.assertEqual('OK', resp.status)
        run_id = resp.content['id']

        steps = list(steps) if steps else []
        run = None
        get_data = {'include': ['executions']}
        while limit:
            resp = client.execute('run', 'get', subject=run_id, data=get_data)
            self.assertEqual('OK', resp.status)
            run = resp.content

            executions = resp.content['executions']
            for e in executions:
                try:
                    steps.remove(e['step'])
                except ValueError:
                    continue

            if not steps:
                break
            limit -= 1
            limit and sleep(wait)
        else:
            raise Exception(
                'Run(id=%s, status=%s) did not execute steps: %s' % (
                    run_id, run['status'], steps))

        return run

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

    def _setup_workflow(self, client, name, specification=None):
        if specification is None:
            specification = Yaml.serialize({
                'name': name,
                'entry': 'step-0',
                'steps': {
                    'step-0': {
                        'operation': 'flux:test-operation',
                    },
                },
            })
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


class TestSimpleRunCases(BaseTestCase):
    def test_duplicate_name_run_on_create1(self, client):
        """Tests creating a run with an existing run name"""
        workflow_name = 'test workflow'
        resp = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        duplicate_name = 'test duplicate name run 1'
        resp = self._setup_run(client, workflow_id, name=duplicate_name)
        self.assertEquals(resp.status, 'OK')

        with self.assertRaises(InvalidError):
            self._setup_run(client, workflow_id, name=duplicate_name)

    def test_duplicate_name_run_on_create2(self, client):
        """Tests creating multiple runs off one workflow without providing a name"""
        workflow_name = 'test workflow'
        resp = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals(resp.status, 'OK')

        resp = self._setup_run(client, workflow_id)
        self.assertEquals(resp.status, 'OK')

    def test_duplicate_name_run_on_update1(self, client):
        """Tests updating a run with an existing run name"""
        workflow_name = 'test workflow'
        resp = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        duplicate_name = 'test duplicate name run 2'
        resp = self._setup_run(client, workflow_id, name=duplicate_name)
        self.assertEquals(resp.status, 'OK')

        resp = self._setup_run(client, workflow_id, 'test duplicate name run 2 a')
        self.assertEquals(resp.status, 'OK')
        run_id = resp.content['id']

        with self.assertRaises(InvalidError):
            client.execute('run', 'update', run_id, {'name': duplicate_name})

    def test_duplicate_name_run_on_update2(self, client):
        """Tests against false positive when updating a run without name change."""
        workflow_name = 'test workflow'
        resp = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        duplicate_name = 'test duplicate name run 3'
        resp = self._setup_run(client, workflow_id, name=duplicate_name)
        self.assertEquals(resp.status, 'OK')
        run_id = resp.content['id']

        resp = client.execute('run', 'update', run_id, {'name': duplicate_name})
        self.assertEquals(resp.status, 'OK')

    def test_run_workflow1(self, client):
        """Tests simple workflow run cycle"""
        workflow_name = 'test run workflow 1'
        resp1 = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp1.status)
        workflow_id = resp1.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEqual('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'completed')

        self.assertTrue(result.pop('ended') >= result.pop('started'))
        expected = {
            'id': run_id,
            'name': workflow_name,
            'parameters': None,
            'workflow_id': workflow_id,
            'products': {},
            'status': 'completed',
        }
        self.assertEquals(expected, result)

    def test_run_workflow2(self, client):
        """Tests simple workflow run and execution cycle"""
        workflow_name = 'test run workflow 2'
        resp1 = self._setup_workflow(client, workflow_name)
        self.assertEqual('OK', resp1.status)
        workflow_id = resp1.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEqual('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'completed', include=['executions'])

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
            'status': 'completed',
            'executions': [{
                'execution_id': 1,
                'ancestor_id': None,
                'step': 'step-0',
                'name': 'Test Operation',
                'status': 'completed',
            }]
        }
        self.assertEquals(expected, result)

    def test_multi_step_run(self, client):
        """Tests for multistep workflow runs"""
        workflow_name = 'test multistep workflow run'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'postoperation': [{
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-1',
                        }],
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'postoperation': [{
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-2',
                        }],
                    }],
                },
                'step-2': {
                    'operation': 'flux:test-operation',
                },
            },
        })
        resp1 = self._setup_workflow(client, workflow_name,
                specification=specification)
        self.assertEqual('OK', resp1.status)
        workflow_id = resp1.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEqual('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'completed', include=['executions'])

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
            'status': 'completed',
            'executions': [
                {
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': 'Test Operation',
                    'status': 'completed',
                },
                {
                    'execution_id': 2,
                    'ancestor_id': ancestor_ids[0],
                    'step': 'step-1',
                    'name': 'Test Operation',
                    'status': 'completed',
                },
                {
                    'execution_id': 3,
                    'ancestor_id': ancestor_ids[1],
                    'step': 'step-2',
                    'name': 'Test Operation',
                    'status': 'completed',
                },
            ]
        }
        self.assertEquals(expected, result)


class TestRunOutcomeCases(BaseTestCase):
    """Tests workflow runs interaction with different outcomes"""
    def test_success_outcome(self, client):
        '''Test successful run outcome'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test sucess outcome'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'completed', ['executions'])

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
            'status': 'completed',
            'executions': [{
                'id': execution['id'],
                'execution_id': 1,
                'ancestor_id': None,
                'step': 'step-0',
                'name': operation_name,
                'status': 'completed',
            }]
        }
        self.assertEquals(expected, result)

    def test_failure_outcome(self, client):
        '''Test failure run outcome'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test failure outcome'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'parameters': {'outcome': 'failed'},
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'failed', ['executions'])

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
            'status': 'failed',
            'executions': [{
                'id': execution['id'],
                'execution_id': 1,
                'ancestor_id': None,
                'step': 'step-0',
                'name': None,
                'name': operation_name,
                'status': 'failed',
            }]
        }
        self.assertEquals(expected, result)

    def test_invalidated_run(self, client):
        '''Test invalidated run outcome'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test invalid run'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'parameters': {'outcome': 'invalidated'},
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'invalidated', ['executions'])

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
            'status': 'invalidated',
            'executions': [{
                'id': execution['id'],
                'execution_id': 1,
                'ancestor_id': None,
                'step': 'step-0',
                'name': operation_name,
                'status': 'invalidated',
            }]
        }
        self.assertEquals(expected, result)

    def test_abort_run(self, client):
        '''Test setting run status to aborted'''
        operation_id = 'flux:test-operation'
        workflow_name = 'test abort run'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'parameters': {'duration': 30},
                    'postoperation': [{
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-1',
                        }],
                    }],
                },
                'step-1': {
                    'operation': operation_id,
                    'parameters': {'duration': 30},
                },
            },
        })

        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id, ('step-0','step-1'))
        run_id = run['id']
        client.execute('run', 'update', subject=run_id, data={'status': 'aborting'})

        result = self._poll_run_status(client, run_id, 'aborted', ['executions'])

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
            'status': 'aborted',
            'executions': [
                {
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': 'Test Operation',
                    'status': 'completed',
                },
                {
                    'execution_id': 2,
                    'ancestor_id': ancestor_ids[0],
                    'step': 'step-1',
                    'name': 'Test Operation',
                    'status': 'aborted',
                },
            ],
        }
        self.assertEquals(expected, result)

    def test_abort_execution(self, client):
        '''Test setting execution status to aborted'''
        operation_id = 'flux:test-operation'
        workflow_name = 'test abort execution'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'parameters': {'duration': 60},
                    'postoperation': [{
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-1',
                        }],
                    }],
                },
                'step-1': {
                    'operation': operation_id,
                    'parameters': {'duration': 30},
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id, ('step-0',))
        run_id = run['id']
        execution_id = run['executions'][-1]['id']
        client.execute('execution', 'update', subject=execution_id, data={'status': 'aborting'})

        result = self._poll_run_status(client, run_id, 'aborted', ['executions'])

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
            'status': 'aborted',
            'executions': [
                {
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': 'Test Operation',
                    'status': 'aborted',
                },
            ],
        }
        self.assertEquals(expected, result)

    def test_success_outcome_with_concurrent_executions(self, client):
        '''Test success run outcome with active concurrent executions'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test success outcome with concurrent executions'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'postoperation': [{
                        'actions': [
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                            }
                        ],
                    }],
                },
                'step-1': {
                    'operation': operation_id,
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'completed', ['executions'])

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        executions = result['executions']
        for execution in executions:
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
            'status': 'completed',
            'executions': [
                {
                    'id': executions[0]['id'],
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': operation_name,
                    'status': 'completed',
                },
                {
                    'id': executions[1]['id'],
                    'execution_id': 2,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'completed',
                },
                {
                    'id': executions[2]['id'],
                    'execution_id': 3,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'completed',
                },
            ]
        }
        self.assertEquals(expected, result)

    def test_failure_outcome_with_concurrent_executions(self, client):
        '''Test failure run outcome with active concurrent executions'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test failure outcome with concurrent executions'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'postoperation': [{
                        'actions': [
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'duration': 60}
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'outcome': 'failed'}
                            }
                        ],
                    }],
                },
                'step-1': {
                    'operation': operation_id,
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'failed', ['executions'])

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        executions = result['executions']
        for execution in executions:
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
            'status': 'failed',
            'executions': [
                {
                    'id': executions[0]['id'],
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': operation_name,
                    'status': 'completed',
                },
                {
                    'id': executions[1]['id'],
                    'execution_id': 2,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'aborted',
                },
                {
                    'id': executions[2]['id'],
                    'execution_id': 3,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'failed',
                },
            ]
        }
        self.assertEquals(expected, result)

    def test_invalidated_outcome_with_concurrent_executions(self, client):
        '''Test invalidated run outcome with active concurrent executions'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test invalidated outcome with concurrent executions'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'postoperation': [{
                        'actions': [
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'duration': 60}
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'outcome': 'invalidated'}
                            }
                        ],
                    }],
                },
                'step-1': {
                    'operation': operation_id,
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'invalidated', ['executions'])

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        executions = result['executions']
        for execution in executions:
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
            'status': 'invalidated',
            'executions': [
                {
                    'id': executions[0]['id'],
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': operation_name,
                    'status': 'completed',
                },
                {
                    'id': executions[1]['id'],
                    'execution_id': 2,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'aborted',
                },
                {
                    'id': executions[2]['id'],
                    'execution_id': 3,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'invalidated',
                },
            ]
        }
        self.assertEquals(expected, result)

class TestIgnoreStatusRuns(BaseTestCase):
    def test_failure(self, client):
        """Test failure run with failed step."""
        name = 'test failure'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test failed operation',
                    'parameters': {'outcome': 'failed'},
                    'postoperation': [{
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-1',
                            'parameters': {'outcome': 'completed'},
                        }],
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test completed operation',
                    'parameters': {'outcome':'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'failed', include=['executions'])

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
            'status': 'failed',
            'parameters': None,
            'products': {},
            'executions': [{
                'execution_id': 1,
                'step': 'step-0',
                'name': 'test failed operation',
                'status': 'failed',
            }],
        }
        self.assertEquals(result, expected)

    def test_ignore_failure(self, client):
        """Test use of ignore failure of failed step."""
        name = 'test ignore failure'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test failed operation',
                    'parameters': {'outcome': 'failed'},
                    'postoperation': [{
                        'terminal': False,
                        'actions': [
                            {
                                'action': 'ignore-step-failure',
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'outcome': 'completed'},
                            }
                        ],
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test operation',
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'failed', include=['executions'])

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
            'status': 'failed',
            'parameters': None,
            'products': {},
            'executions': [
                {
                    'execution_id': 1,
                    'step': 'step-0',
                    'name': 'test failed operation',
                    'status': 'failed',
                },
                {
                    'execution_id': 2,
                    'step': 'step-1',
                    'name': 'test operation',
                    'status': 'completed',
                },
            ],
        }
        self.assertEquals(result, expected)

    def test_ignore_failure_incorrect_use(self, client):
        """Test failure with ignore step with incorrect use case."""
        name = 'test ignore failure bad case'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test failed operation',
                    'parameters': {'outcome': 'failed'},
                    'postoperation': [{
                        'terminal': False,
                        'actions': [
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'outcome': 'completed'},
                            },
                            {
                                'action': 'ignore-step-failure',
                            },
                        ],
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test operation',
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'failed', include=['executions'])

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
            'status': 'failed',
            'parameters': None,
            'products': {},
            'executions': [{
                'execution_id': 1,
                'step': 'step-0',
                'name': 'test failed operation',
                'status': 'failed',
            }],
        }
        self.assertEquals(result, expected)

class TestRunTimedoutCases(BaseTestCase):
    """Test run cases involving the timedout status."""
    def test_timedout_case(self, client):
        """Test timedout with multi-step run."""
        name = 'test timedout run'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test timedout operation',
                    'timeout': 1,
                    'parameters': {'duration': 100},
                    'postoperation': [{
                        'terminal': False,
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-1',
                            'parameters': {'outcome': 'completed'},
                        }],
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test completed operation',
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'timedout', include=['executions'])

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
            'status': 'timedout',
            'parameters': None,
            'products': {},
            'executions': [
                {
                    'execution_id': 1,
                    'step': 'step-0',
                    'name': 'test timedout operation',
                    'status': 'timedout',
                },
            ],
        }
        self.assertEquals(result, expected)

    def test_timedout_run_with_concurrent_executions(self, client):
        '''Test timedout run with active concurrent executions'''
        operation_id = 'flux:test-operation'
        operation_name = 'Test Operation'
        workflow_name = 'test timedout run with concurrent executions'
        specification = Yaml.serialize({
            'name': workflow_name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': operation_id,
                    'postoperation': [{
                        'actions': [
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'duration': 160}
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-2',
                                'parameters': {'duration': 100},
                            }
                        ],
                    }],
                },
                'step-1': {
                    'operation': operation_id,
                },
                'step-2': {
                    'timeout': 1,
                    'operation': operation_id,
                },
            },
        })
        resp = self._setup_workflow(client, workflow_name, specification=specification)
        self.assertEqual('OK', resp.status)
        workflow_id = resp.content['id']

        run = self._setup_active_run(client, workflow_id)
        run_id = run['id']
        result = self._poll_run_status(client, run_id, 'timedout', include=['executions'])

        run_ended = result.pop('ended')
        run_started = result.pop('started')

        executions = result['executions']
        for execution in executions:
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
            'status': 'timedout',
            'executions': [
                {
                    'id': executions[0]['id'],
                    'execution_id': 1,
                    'ancestor_id': None,
                    'step': 'step-0',
                    'name': operation_name,
                    'status': 'completed',
                },
                {
                    'id': executions[1]['id'],
                    'execution_id': 2,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-1',
                    'name': operation_name,
                    'status': 'aborted',
                },
                {
                    'id': executions[2]['id'],
                    'execution_id': 3,
                    'ancestor_id': executions[0]['id'],
                    'step': 'step-2',
                    'name': operation_name,
                    'status': 'timedout',
                },
            ]
        }
        self.assertEquals(expected, result)

    def test_ignore_timedout_case(self, client):
        """Test ignore-failure on timedout step."""
        name = 'test ignore timedout run'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test timedout operation',
                    'timeout': 1,
                    'parameters': {'duration': 100},
                    'postoperation': [{
                        'terminal': False,
                        'actions': [
                            {
                                'action': 'ignore-step-failure',
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'outcome': 'completed'},
                            }
                        ],
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test completed operation',
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'timedout', include=['executions'])

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
            'status': 'timedout',
            'parameters': None,
            'products': {},
            'executions': [
                {
                    'execution_id': 1,
                    'step': 'step-0',
                    'name': 'test timedout operation',
                    'status': 'timedout',
                },
                {
                    'execution_id': 2,
                    'step': 'step-1',
                    'name': 'test completed operation',
                    'status': 'completed',
                },
            ],
        }
        self.assertEquals(result, expected)

class TestInvalidRunCase(BaseTestCase):
    """Test run cases involving invalidated status."""
    def test_invalidated_case(self, client):
        """Test invalidated run with multi-step run."""
        name = 'test invalidated run'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test invalid operation',
                    'parameters': {'outcome': 'invalidated'},
                    'postoperation': [{
                        'actions': [{
                            'action': 'execute-step',
                            'step': 'step-1',
                            'parameters': {'outcome': 'completed'},
                        }],
                        'terminal': False,
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test completed operation',
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        run = self._poll_run_status(client, run_id, 'invalidated', ['executions'])
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
            'status': 'invalidated',
            'parameters': None,
            'products': {},
            'executions': [
                {
                    'execution_id': 1,
                    'step': 'step-0',
                    'name': 'test invalid operation',
                    'status': 'invalidated',
                },
            ],
        }
        self.assertEquals(result, expected)

    def test_ignore_invalidated_case(self, client):
        name = 'test ignore invalidated run'
        specification = Yaml.serialize({
            'name': name,
            'entry': 'step-0',
            'steps': {
                'step-0': {
                    'operation': 'flux:test-operation',
                    'description': 'test invalid operation',
                    'parameters': {'outcome': 'invalidated'},
                    'postoperation': [{
                        'actions': [
                            {
                                'action': 'ignore-step-failure',
                            },
                            {
                                'action': 'execute-step',
                                'step': 'step-1',
                                'parameters': {'outcome': 'completed'},
                            },
                        ],
                        'terminal': False,
                    }],
                },
                'step-1': {
                    'operation': 'flux:test-operation',
                    'description': 'test completed operation',
                    'parameters': {'outcome': 'completed'},
                },
            },
        })
        resp = self._setup_workflow(client, name, specification)
        self.assertEquals('OK', resp.status)
        workflow_id = resp.content['id']

        resp = self._setup_run(client, workflow_id)
        self.assertEquals('OK', resp.status)
        run_id = resp.content['id']

        result = self._poll_run_status(client, run_id, 'invalidated', include=['executions'])
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
            'status': 'invalidated',
            'parameters': None,
            'products': {},
            'executions': [
                {
                    'execution_id': 1,
                    'step': 'step-0',
                    'name': 'test invalid operation',
                    'status': 'invalidated',
                },
            ],
        }
        self.assertEquals(result, expected)
