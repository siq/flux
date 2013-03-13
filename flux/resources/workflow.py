from mesh.standard import *
from scheme import *

class Workflow(Resource):
    """A workflow."""

    name = 'workflow'
    version = 1
    requests = 'create delete get load put query update'

    class schema:
        id = UUID(nonnull=True, oncreate=True, operators='equal')
        name = Text(nonempty=True, operators='equal')
        designation = Token(operators='equal')
        specification = Text(nonempty=True)
        modified = DateTime(utc=True, readonly=True)

    class create(Resource.create):
        support_returning = True

    class generate:
        endpoint = ('GENERATE', 'workflow')
        title = 'Generate a workflow specification'
        schema = {
            'name': Text(nonempty=True),
            'operations': Sequence(Structure({
                'operation': Token(segments=2, nonempty=False),
                'parameters': Field(),
            }), min_length=1, nonempty=True),
        }
        responses = {
            OK: Response({
                'name': Text(nonempty=True),
                'specification': Text(nonempty=True)
            }),
            INVALID: Response(Errors),
        }

    class update(Resource.update):
        support_returning = True
