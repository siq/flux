from mesh.standard import OperationError, bind
from scheme import current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

from flux.bindings import platoon
from flux.constants import *
from flux.models.execution import WorkflowExecution
from flux.models.workflow import Workflow

__all__ = ('Run',)

Event = bind(platoon, 'platoon/1.0/event')

schema = Schema('flux')
log = LogHelper('flux')

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
    products = Json()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)

    executions = relationship(WorkflowExecution, backref='run',
        cascade='all,delete-orphan', lazy='dynamic', passive_deletes=True,
        order_by=WorkflowExecution.execution_id)

    def __repr__(self):
        return 'Run(id=%r, name=%r, status=%r)' % (self.id, self.name, self.status)

    @property
    def active_executions(self):
        active_statuses = ACTIVE_RUN_STATUSES.split(' ')
        return self.executions.filter(
                WorkflowExecution.status.in_(active_statuses))

    @property
    def is_active(self):
        return self.status in ACTIVE_RUN_STATUSES.split(' ')

    @property
    def next_execution_id(self):
        return len(self.executions.all()) + 1

    def abort_executions(self, session):
        for execution in self.active_executions.with_lockmode('update').all():
            execution.abort(session)

    def complete(self, session):
        self._end_run(session, 'completed')
        Event.create(topic='run:completed', aspects={'id': self.id})

    def contribute_values(self):
        run = {'id': self.id, 'name': self.name, 'started': self.started}
        if self.parameters:
            run['env'] = self.parameters
        else:
            run['env'] = {}
        return {'run': run}

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
        return WorkflowExecution.create(
                session, run_id=self.id, execution_id=self.next_execution_id,
                ancestor=ancestor, step=step, name=name, parameters=parameters)

    def fail(self, session):
        self._end_run(session, 'failed')
        self.abort_executions(session)

    def initiate(self, session):
        self.started = current_timestamp()
        self.workflow.workflow.initiate(session, self)

    def initiate_abort(self, session):
        self._end_run(session, 'aborted')

    def invalidate(self, session):
        self._end_run(session, 'invalidated')
        self.abort_executions(session)

    def timeout(self, session):
        self._end_run(session, 'timedout')
        self.abort_executions(session)

    def update_products(self, products):
        if not isinstance(products, dict):
            raise ValueError(products)
        elif not products:
            return

        if self.products:
            self.products.update(products)
        else:
            self.products = products

    def _end_run(self, session, status):
        self.status = status
        self.ended = current_timestamp()

        try:
            Event.create(topic='run:changed', aspects={'id': self.id})
        except Exception:
            log('exception', 'failed to fire run:changed event')
