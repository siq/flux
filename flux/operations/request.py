from mesh.standard import ValidationError, bind
from scheme import *
from scheme.surrogate import surrogate
from spire.schema import NoResultFound
from spire.support.logs import LogHelper
from spire.util import uniqid

from flux.models.request import Request as RequestModel
from flux.operations.operation import *

__all__ = ('CreateRequest',)

log = LogHelper('flux')

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
        process_id = data['process_id']
        try:
            subject = RequestModel.load(session, id=data['request_id'])
        except NoResultFound:
            return self.push(process_id, self.outcome('failed'))

        outcome = ('completed' if subject.status == 'completed' else 'failed')
        self.push(process_id, self.outcome(outcome, {
            'request': surrogate.construct('flux.surrogates.request', subject),
        }))

    def initiate(self, session, data):
        Request = self.docket_entity.bind('docket.entity/1.0/flux/1.0/request')
        id = uniqid()

        attrs = data['input']
        try:
            attrs = self.operation['schema'].unserialize(attrs)
        except ValidationError:
            log('exception', 'initiation of create-request operation failed')
            return self.invalidation(error='invalid-input')

        wait_for_completion = attrs.pop('wait_for_completion', True)
        if wait_for_completion:
            SubscribedTask.queue_http_task('complete-request-operation',
                self.flux.prepare('flux/1.0/request', 'task', None,
                    {'task': 'complete-request-operation', 'request_id': id,
                        'process_id': data['id']}),
                topic='request:completed',
                aspects={'id': id},
                timeout=259200)

        attrs['id'] = id
        try:
            request = Request.create(**attrs)
        except Exception:
            log('exception', 'initiation of create-request operation failed')
            return self.invalidation(error='failed')

        if wait_for_completion:
            return self.executing()
        else:
            outcome = ('created' if request.status in ('pending', 'prepared') else 'failed')
            return self.outcome(outcome, {
                'request': surrogate.construct('flux.surrogates.request', request),})
