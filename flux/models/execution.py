from spire.schema import *

schema = Schema('flux')

class Execution(Model):
    """A step execution."""

    class meta:
        constraints = [UniqueConstraint('run_id', 'execution_id')]
        schema = schema
        tablename = 'execution'

    id = Identifier()
    run_id = ForeignKey('run.id', nullable=False, ondelete='CASCADE')
    execution_id = Integer(minimum=1, nullable=False)
    ancestor_id = ForeignKey('Execution')
    step = Token(nullable=False)
    name = Text()
    status = Enumeration('pending active completed aborted', nullable=False, default='pending')
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)
    parameters = Json()

    descendants = relationship('Execution', backref='ancestor')

    @classmethod
    def create(cls, session, **attrs):
        execution = cls(**attrs)
        session.add(execution)
        return execution
