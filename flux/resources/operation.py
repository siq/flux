from mesh.standard import *
from scheme import *

from flux.constants import *

Outcome = Structure({
    'description': Text(),
    'outcome': Enumeration('success failure', nonempty=True),
    'schema': Definition(),
}, name='outcome', nonnull=True)

class Operation(Resource):
    """A workflow operation."""

    name = 'operation'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = Token(segments=2, nonempty=True, oncreate=True, operators='equal')
        name = Text(nonempty=True, operators='equal')
        phase = Enumeration(OPERATION_PHASES, nonempty=True, operators='equal')
        description = Text()
        schema = Definition()
        outcomes = Map(Outcome, nonempty=True)

    class operation:
        endpoint = ('OPERATION', 'operation')
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

    class process:
        endpoint = ('PROCESS', 'operation/id')
        specific = True
        schema = Structure({
            'id': UUID(nonempty=True),
            'tag': Text(nonempty=True),
            'subject': Token(nonempty=True),
            'info': Field(),
            'status': Enumeration('executing aborted completed failed timedout', nonnull=True),
            'output': Field(),
            'progress': Field(),
        }, nonempty=True)
        responses = {
            OK: Response(),
            INVALID: Response(Errors),
        }

    class task:
        endpoint = ('TASK', 'operation')
        title = 'Initiating an operation task'
        schema = Structure(
            structure={
                'complete-test-operation': {
                    'state': Field(),
                },
            },
            nonempty=True,
            polymorphic_on='task')
        responses = {
            OK: Response(),
            INVALID: Response(Errors),
        }
