from scheme import *
from spire.util import uniqid

from flux.operations.operation import *

__all__ = ('CreateRequest',)

class CreateRequest(Operation):
    """A workflow operation which creates a request."""

    id = 'flux:create-request'
    endpoint = ('flux/1.0/request', 'operation')
    operation = {
        'id': 'flux:create-request',
        'name': 'Create Request',
        'phase': 'operation',
        'schema': Structure({
            'name': Text(nonempty=True),
            'description': Text(),
            'status': Enumeration('prepared pending', nonnull=True),
            'originator': Token(nonempty=True),
            'assignee': Token(),
            'attachments': Sequence(Structure({
                'token': Token(),
                'title': Text(),
                'attachment': Surrogate(nonempty=True),
            }, nonempty=True)),
            'slots': Map(key=Token(nonempty=True), value=Structure({
                'title': Text(),
                'slot': Token(nonempty=True),
            }, nonempty=True)),
            'message': Structure({
                'author': Token(nonempty=True),
                'message': Text(nonempty=True),
            }),
            'wait_for_completion': Boolean(default=True),
        }),
        'outcomes': {
            'created': {
                'outcome': 'success',
                'schema': Structure({
                    'request': Surrogate(nonempty=True),
                }),
            },
            'completed': {
                'outcome': 'success',
                'schema': Structure({
                    'request': Surrogate(nonempty=True),
                }),
            },
            'failed': {
                'outcome': 'failure',
                'schema': Structure({
                    'request': Surrogate(),
                }),
            },
        },
    }

    def complete(self, session, data):
        pass

    def initiate(self, session, data):
        pass
