from scheme import *
from scheme.surrogate import surrogate
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
            'output': Map(Surrogate(nonempty=True), Token(nonempty=True)),
            'duration': Integer(default=5),
            'delay_abort': Boolean(default=False),
        }),
        'outcomes': {
            'completed': {
                'outcome': 'success',
                'schema': Map(Surrogate(nonempty=True), Token(nonempty=True)),
            },
            'failed': {
                'outcome': 'failure',
                'schema': Map(Surrogate(nonempty=True), Token(nonempty=True)),
            },
        },
    }

    def abort(self, session, data):
        process_id = data['id']

        state = data['state']
        if state and state.get('delay_abort'):
            return

        self.push(process_id, self.aborted())

    def complete(self, session, data):
        id = data['state']['id']
        input = data['state'].get('input') or {}

        expected_outcome = input.get('outcome', 'completed')
        output = input.get('output')
        if output:
            output = {k: surrogate(v) for k,v in output.iteritems()}
        else:
            output = None
        if expected_outcome in ('completed', 'failed'):
            self.push(id, self.outcome(expected_outcome, output))

    def initiate(self, session, data):
        input = data.get('input') or {}
        if input.get('outcome') == 'invalidated':
            return self.invalidation(error='failed')

        ScheduledTask.queue_http_task('complete-test-operation',
            self.flux.prepare('flux/1.0/operation', 'task', None,
                {'task': 'complete-test-operation', 'state': data}),
            delta = input.get('duration', 5))

        return self.executing(state={'delay_abort': input.get('delay_abort')})

    def report(self, session, data):
        return {'status': 'executing', 'state': data.get('state')}
