from spire.mesh import Definition
from spire.schema import *
from spire.support.logs import LogHelper

log = LogHelper('flux')
schema = Schema('flux')

class Action(Model):
    """A workflow action."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'action'

    id = Token(segments=2, nullable=False, primary_key=True)
    name = Text(nullable=False)
    description = Text()
    phase = Enumeration('preoperation postoperation unrestricted', nullable=False)
    schema = Definition(nullable=False)
    type = Enumeration('mesh internal', nullable=False)

class InternalAction(Action):
    """An internal workflow action."""

    class meta:
        polymorphic_identity = 'internal'
        schema = schema
        tablename = 'internal_action'

    action_id = ForeignKey('action.id', nullable=False, primary_key=True)
    implementation = Text(nullable=False)
