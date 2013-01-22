from mesh.standard import *
from scheme import *

PHASES = 'preoperation postoperation prerun postrun unrestricted'

class Action(Resource):
    """An action."""

    name = 'action'
    version = 1
    requests = 'create delete get put query update'

    class schema:
        id = Token(segments=2, nonempty=True, oncreate=True, operators='equal')
        name = Text(nonempty=True, operators='equal')
        description = Text()
        phase = Enumeration(PHASES, nonempty=True)
        schema = Definition()
