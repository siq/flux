from mesh.standard import *
from scheme import *

from flux.constants import *

__all__ = ('Execution',)

class Execution(Resource):
    """A step execution."""

    name = 'execution'
    version = 1
    requests = 'get query update'

    class schema:
        id = UUID(readonly=True, operators='equal')
        run_id = UUID(readonly=True, operators='equal')
        execution_id = Integer(readonly=True, operators='equal')
        ancestor_id = UUID(readonly=True, operators='equal')
        step = Token(segments=2, readonly=True, operators='equal')
        name = Text()
        status = Enumeration(RUN_STATUSES, nonnull=True, oncreate=False),
        started = DateTime(utc=True, readonly=True)
        ended = DateTime(utc=True, readonly=True)
        parameters = Field(readonly=True)

    class update(Resource.update):
        fields = {
            'status': Enumeration('aborted', nonempty=True),
        }
