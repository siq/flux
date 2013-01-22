from spire.schema import *

schema = Schema('flux')

class Step(Model):
    """A workflow step execution."""

    class meta:
        constraints = [UniqueConstraint('run_id', 'step_id')]
        schema = schema
        tablename = 'step'

    id = Identifier()
    run_id = ForeignKey('run.id', nullable=False, ondelete='CASCADE')
    step_id = Integer(minimum=1, nullable=False)
    ancestor_id = ForeignKey('step.id', ondelete='SET NULL')
    step = Token(segments=2, nullable=False)
    name = Text()
    status = Enumeration('pending active completed aborted', nullable=False, default='pending')
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)
    parameters = Json()

    descendants = relationship('Step', backref=backref('ancestor', remote_side=[id]))
