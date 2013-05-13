from scheme import *
from spire.util import uniqid

from flux.operations.operation import *

__all__ = ('TestOperation', 'TestFailedOperation',)

class TestOperation(Operation):
    """A test operation."""

    id = 'flux:test-operation'
    endpoint = ('flux/1.0/operation', 'operation')
    operation = {
        'id': 'flux:test-operation',
        'name': 'Test Operation',
        'phase': 'operation',
        'schema': Structure({
            'outcome': Token(default='completed'),
            'duration': Integer(default=5),
        }),
        'outcomes': {
            'completed': {'outcome': 'success'},
        },
    }

    def complete(self, session, data):
        id = data['state']['id']
        input = data['state'].get('input') or {}

        expected_outcome = input.get('outcome', 'completed')
        if expected_outcome == 'completed':
            self.push(id, outcome('completed'))

    def initiate(self, session, data):
        input = data.get('input') or {}
        ScheduledTask.queue_http_task('complete-test-operation',
            self.flux.prepare('flux/1.0/operation', 'task', None,
                {'task': 'complete-test-operation', 'state': data}),
            delta = input.get('duration', 5))

        return executing()

class TestFailedOperation(Operation):
    """A test failed operation."""

    id = 'flux:test-failed-operation'
    endpoint = ('flux/1.0/operation', 'operation')
    operation = {
        'id': 'flux:test-failed-operation',
        'name': 'Test Failed Operation',
        'phase': 'operation',
        'schema': Structure({
            'outcome': Token(default='completed'),
            'duration': Integer(default=5),
        }),
        'outcomes': {
            'completed': {'outcome': 'failure'},
        },
    }

    def complete(self, session, data):
        id = data['state']['id']
        input = data['state'].get('input') or {}

        expected_outcome = input.get('outcome', 'completed')
        if expected_outcome == 'completed':
            self.push(id, outcome('completed'))

    def initiate(self, session, data):
        input = data.get('input') or {}
        ScheduledTask.queue_http_task('complete-test-operation',
            self.flux.prepare('flux/1.0/operation', 'task', None,
                {'task': 'complete-test-operation', 'state': data}),
            delta = input.get('duration', 5))

        return executing()
