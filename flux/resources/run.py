from mesh.standard import *
from scheme import *
from scheme.supplemental import Email

from flux.constants import *

class Run(Resource):
    """A workflow run."""

    name = 'run'
    version = 1
    requests = 'create delete get load query update'

    class schema:
        id = UUID(nonnull=True, oncreate=True, operators='equal')
        workflow_id = UUID(nonempty=True, onupdate=False, operators='equal')
        name = Text(operators='equal')
        status = Enumeration(RUN_STATUSES)
        parameters = Field(onupdate=False)
        products = Map(Field(nonempty=True), readonly=True)
        started = DateTime(utc=True, readonly=True)
        ended = DateTime(utc=True, readonly=True)
        executions = Sequence(Structure({
            'id': UUID(nonempty=True),
            'execution_id': Integer(),
            'ancestor_id': UUID(),
            'step': Token(),
            'name': Text(),
            'status': Enumeration(RUN_STATUSES, nonnull=True),
            'started': DateTime(),
            'ended': DateTime(),
        }), readonly=True, deferred=True)

    class create(Resource.create):
        support_returning = True
        fields = {
            'notify': Email(nonnull=True, min_length=1, multiple=True),
            'status': Enumeration('prepared pending', nonnull=True),
        }

    class update(Resource.update):
        support_returning = True
        fields = {
            'status': Enumeration('aborted pending', ignored_values='active completed'
                ' failed invalidated prepared suspended timedout waiting'),
        }

    class task:
        endpoint = ('TASK', 'run')
        title = 'Initiating a run task'
        schema = Structure(
            structure={
                'abort-executions': {
                    'id': UUID(nonempty=True),
                },
                'initiate-run': {
                    'id': UUID(nonempty=True),
                },
                'run-completion' : {
                    'id': UUID(nonempty=True),
                    'notify': Text(nonempty=True)
                },
            },
            nonempty=True, polymorphic_on='task')
        responses = {
            OK: Response(),
            INVALID: Response(Errors),
        }
