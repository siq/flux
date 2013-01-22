from mesh.standard import *
from scheme import *

Endpoint = Structure(
    structure={
        'http': {
            'url': Text(nonempty=True),
            'method': Text(nonempty=True, default='POST'),
            'mimetype': Text(nonempty=True, default='application/json'),
            'headers': Map(Text(nonempty=True), nonnull=True),
        }
    },
    polymorphic_on=Enumeration('http', name='type', nonempty=True),
    nonnull=True)

class Executor(Resource):
    """A workflow executor."""

    name = 'executor'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = Token(nonempty=True, oncreate=True, operators='equal')
        description = Text()
        status = Enumeration('active inactive disabled', oncreate=False, nonnull=True)
        endpoints = Map(Endpoint, nonempty=True)
