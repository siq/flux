from mesh.standard import OperationError, bind
from scheme import current_timestamp
from spire.mesh import Surrogate
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.constants import *
from scheme import current_timestamp
from flux.models.Request import Request

__all__ = ('Message',)

schema = Schema('flux')
log = LogHelper('flux')

class Message(Model):
    """A message."""

    class meta:
        schema = schema
        tablename = 'message'

    id = Identifier()
    request_id = ForeignKey('request.id', nullable=False, ondelete='CASCADE')
    author = Token(nullable=False)
    occurrence = DateTime(nullable=False, timezone=True)
    message = Text()

    @classmethod
    def create(cls, session, request_id, **attrs):
        msg = cls(occurrence=current_timestamp(), **attrs)
        try:
            msg.request_id = Request.load(session, id=request_id).id
        except NoResultFound:
            raise OperationError(token='unknown-request')

        session.add(msg)
        return msg