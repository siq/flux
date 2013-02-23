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