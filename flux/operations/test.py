from scheme import *
from spire.util import uniqid

from flux.operations.operation import *

__all__ = ('TestOperation',)

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

        outcome = input.get('outcome', 'completed')
        if outcome == 'completed':
            self.push(id, status='completed', output={'outcome': 'completed'})

    def initiate(self, session, data):
        input = data.get('input') or {}
        ScheduledTask.queue_http_task('complete-test-operation',
            self.flux.prepare('flux/1.0/operation', 'task', None,
                {'task': 'complete-test-operation', 'state': data}),
            delta = input.get('duration', 5))

        return {'status': 'executing'}
