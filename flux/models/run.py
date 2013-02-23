from mesh.standard import OperationError
from spire.schema import *

from flux.constants import *
from flux.models.execution import Execution
from flux.models.workflow import Workflow

__all__ = ('Run',)

schema = Schema('flux')

class Run(Model):
    """A workflow run."""

    class meta:
        schema = schema
        tablename = 'run'

    id = Identifier()
    workflow_id = ForeignKey('workflow.id', nullable=False)
    name = Text(nullable=False)
    status = Enumeration(RUN_STATUSES, nullable=False, default='pending')
    parameters = Json()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)

    executions = relationship(Execution, backref='run')

    @property
    def next_execution_id(self):
        return len(self.executions) + 1

    @classmethod
    def create(cls, session, workflow_id, name=None, **attrs):
        try:
            workflow = Workflow.load(session, id=workflow_id)
        except NoResultFound:
            raise OperationError('unknown-workflow')

        if not name:
            name = workflow.name

        run = cls(name=name, workflow_id=workflow.id, **attrs)
        session.add(run)
        return run

    def create_execution(self, session, step, parameters=None, ancestor=None, name=None):
        return Execution.create(session, run_id=self.id, execution_id=self.next_execution_id,
            ancestor=ancestor, step=step, name=name, parameters=parameters)

    def initiate(self, session):
        workflow = self.workflow.workflow
        workflow.initiate(session, self)