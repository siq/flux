from mesh.standard import *
from scheme import *

class Message(Resource):
    """A request message."""

    name = 'message'
    version = 1

    class schema:
        id = UUID(operators='equal')
        request_id = UUID(nonempty=True, operators='equal')
        author = UUID(nonnull=True, operators='equal')
        occurrence = DateTime(utc=True, readonly=True, sortable=True)
        message = Text()
