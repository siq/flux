from mesh.standard import *
from scheme import *

from flux.constants import *

__all__ = ('Request',)

class Request(Resource):
    """A request."""

    name = 'request'
    version = 1
    requests = 'create delete get load query update'

    class schema:
        id = UUID(nonnull=True, oncreate=True, operators='equal')
        name = Text(nonempty=True, operators='equal icontains')
        status = Enumeration(REQUEST_STATUSES, operators='equal')
        originator = Token(nonempty=True, operators='equal')
        assignee = Token(nonnull=True, operators='equal')
        attachments = Sequence(Structure({
            'token': Token(),
            'title': Text(),
            'attachment': Surrogate(nonempty=True),
        }, nonempty=True))
        slots = Map(key=Token(nonempty=True), value=Structure({
            'title': Text(),
            'slot': Token(nonempty=True),
        }, nonempty=True))
        slot_order = Sequence(Token(nonempty=True))
        products = Map(key=Token(nonempty=True), value=Structure({
            'title': Text(),
            'product': Surrogate(nonempty=True),
        }, nonempty=True), readonly=True)
        template = Text(onupdate=False, deferred=True)
        form = Structure({
            'schema': Definition(),
            'layout': Sequence(Structure({
                'title': Text(),
                'elements': Sequence(Structure({
                    'type': Token(),
                    'field': Token(),
                    'label': Text(),
                    'options': Field(),
                })),
            })),
        }, deferred=True, readonly=True)
        entities = Map(key=Token(nonempty=True), value=Text(nonempty=True),
            nonnull=True, oncreate=False, deferred=True)

    class create(Resource.create):
        support_returning = True
        fields = {
            'status': Enumeration('prepared pending', nonnull=True),
            'message': Structure({
                'author': Token(nonempty=True),
                'message': Text(nonempty=True),
            }),
        }

    class operation:
        endpoint = ('OPERATION', 'request')
        schema = Structure({
            'id': UUID(nonempty=True),
            'tag': Text(nonempty=True),
            'subject': Token(nonempty=True),
            'status': Token(nonempty=True),
            'input': Field(),
            'state': Field(),
        }, nonempty=True)
        responses = {
            OK: Response({
                'status': Token(nonempty=True),
                'output': Field(),
                'progress': Field(),
                'state': Field(),
            }),
            INVALID: Response(Errors),
        }

    class task:
        endpoint = ('TASK', 'request')
        title = 'Initiating a request task'
        schema = Structure(
            structure={
                'initiate-request': {
                    'id': UUID(nonempty=True),
                },
                'complete-request-operation': {
                    'process_id': UUID(nonempty=True), 
                    'request_id': UUID(nonempty=True),
                },
                'cancel-request': {
                    'id': UUID(nonempty=True),
                },
                'decline-request': {
                    'id': UUID(nonempty=True),
                },
            },
            nonempty=True,
            polymorphic_on='task')
        responses = {
            OK: Response(),
            INVALID: Response(Errors),
        }

    class update(Resource.update):
        support_returning = True
