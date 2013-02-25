from scheme import current_timestamp
from spire.schema import *

from flux.constants import *

schema = Schema('flux')

__all__ = ('Execution',)

class Execution(Model):
    """A step execution."""

    class meta:
        constraints = [UniqueConstraint('run_id', 'execution_id')]
        schema = schema
        tablename = 'execution'

    id = Identifier()
    run_id = ForeignKey('run.id', nullable=False, ondelete='CASCADE')
    execution_id = Integer(minimum=1, nullable=False)
    ancestor_id = ForeignKey('execution.id')
    step = Token(nullable=False)
    name = Text()
    status = Enumeration(RUN_STATUSES, nullable=False, default='pending')
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)
    parameters = Json()

    descendants = relationship('Execution',
        backref=backref('ancestor', remote_side=[id]))

    @property
    def workflow(self):
        return self.run.workflow

    @classmethod
    def create(cls, session, **attrs):
        execution = cls(started=current_timestamp(), **attrs)
        session.add(execution)
        return execution

    def complete(self, session, status, output):
        execution.ended = current_timestamp()
        execution.status = status

        workflow = self.workflow.workflow
        step = workflow.steps[self.step]

        step.complete(session, self, workflow, output)

    def update_progress(self, session, progress):
        # TODO: handle progress_update
        self.status = 'executing'
