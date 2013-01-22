from mesh.standard import *
from scheme import *

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
        description = Text()
        schema = Definition()
        outcomes = Map(Outcome, nonnull=True)
