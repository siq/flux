from mesh.standard import *
from scheme import *

__all__ = ('EmailTemplate',)

class EmailTemplate(Resource):
    """An email template."""

    name = 'emailtemplate'
    version = 1
    requests = 'create delete get load query update'

    class schema:
        id = UUID(nonnull=True, oncreate=True, operators='equal')
        template = Text(nonempty=True, operators='equal')
