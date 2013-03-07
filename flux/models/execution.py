from scheme import current_timestamp
from spire.schema import *

from flux.constants import *

schema = Schema('flux')

__all__ = ('WorkflowExecution',)

class WorkflowExecution(Model):
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

    descendants = relationship('WorkflowExecution',
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
        self.ended = current_timestamp()
        self.status = status

        workflow = self.workflow.workflow
        step = workflow.steps[self.step]

        step.complete(session, self, workflow, output)

    def update_progress(self, session, progress):
        # TODO: handle progress_update
        self.status = 'executing'
