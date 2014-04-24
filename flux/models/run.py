from mesh.standard import bind, OperationError, ValidationError
from scheme import current_timestamp
from spire.mesh import Surrogate
from spire.schema import *
from spire.support.logs import LogHelper
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.bindings import platoon
from flux.constants import *
from flux.models.execution import WorkflowExecution
from flux.models.workflow import Workflow

__all__ = ('Product', 'Run')

Event = bind(platoon, 'platoon/1.0/event')

schema = Schema('flux')
log = LogHelper('flux')

class Product(Model):
    """A workflow product."""

    class meta:
        constraints = [UniqueConstraint('run_id', 'token')]
        schema = schema
        tablename = 'product'

    id = Identifier()
    run_id = ForeignKey('run.id', nullable=False, ondelete='CASCADE')
    token = Token(nullable=False)
    product = Surrogate(nullable=False)

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

    executions = relationship(WorkflowExecution, backref='run',
        cascade='all,delete-orphan', lazy='dynamic', passive_deletes=True,
        order_by=WorkflowExecution.execution_id)
    products = relationship(Product, backref='run',
        collection_class=attribute_mapped_collection('token'),
        cascade='all,delete-orphan', passive_deletes=True)

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
        for execution in self.active_executions.all():
            session.begin_nested()
            try:
                session.refresh(execution, lockmode='update')
                execution.initiate_abort(session)
            except Exception:
                session.rollback()
            else:
                session.commit()

    def associate_product(self, token, product):
        self.products[token] = Product(product=product, token=token)

    def complete(self, session):
        self._end_run(session, 'completed')

    def contribute_values(self):
        run = {'id': self.id, 'name': self.name, 'started': self.started}
        parameters = {}

        workflow = self.workflow.workflow
        if workflow.parameters:
            parameters.update(workflow.parameters)

        if self.parameters:
            if workflow.schema:
                parameters.update(workflow.schema.process(self.parameters,
                    serialized=True, partial=True))
            else:
                parameters.update(self.parameters)

        run['env'] = parameters
        return {'run': run}

    @classmethod
    def create(cls, session, workflow_id, name=None, parameters=None, **attrs):
        try:
            workflow = Workflow.load(session, id=workflow_id)
        except NoResultFound:
            raise OperationError('unknown-workflow')

        workflow_schema = workflow.workflow.schema
        if workflow_schema and parameters:
            workflow_schema.process(parameters, serialized=True, partial=True)

        if name:
            if session.query(cls).filter_by(name=name).count():
                raise OperationError(token='duplicate-run-name')
        else:
            name = workflow.name

        run = cls(name=name, workflow_id=workflow.id, parameters=parameters, **attrs)
        session.add(run)
        return run

    def create_execution(self, session, step, parameters=None, ancestor=None, name=None):
        return WorkflowExecution.create(
                session, run_id=self.id, execution_id=self.next_execution_id,
                ancestor=ancestor, step=step, name=name, parameters=parameters)

    def fail(self, session):
        self._end_run(session, 'failed')
        self.abort_executions(session)

    def get_products(self):
        products = {}
        for token, product in self.products.iteritems():
            products[token] = product.product
        return products

    def initiate(self, session):
        self.started = current_timestamp()
        session.begin_nested()

        try:
            self.workflow.workflow.initiate(session, self)
        except Exception:
            log('exception', 'initiation of %r failed due to exception', self)
            session.rollback()
            self.invalidate(session)
        else:
            session.commit()

    def abort(self, session):
        self._end_run(session, 'aborted')

    def invalidate(self, session):
        self._end_run(session, 'invalidated')
        self.abort_executions(session)

    def timeout(self, session):
        self._end_run(session, 'timedout')
        self.abort_executions(session)

    def update(self, session, **attrs):
        task = None
        name = attrs.get('name')
        if name and name != self.name:
            if session.query(Run).filter_by(name=name).count():
                raise OperationError(token='duplicate-run-name')

        status = attrs.get('status')
        if status:
            if status == 'pending':
                if self.status != 'prepared':
                    raise ValidationError('invalid-transition')
                task = 'initiate'
            elif status == 'aborting':
                if self.is_active:
                    task = 'abort'
                elif self.status != 'aborting':
                    raise ValidationError('invalid-transition')

        self.update_with_mapping(attrs, ignore='id')
        return task

    def _end_run(self, session, status):
        self.status = status
        self.ended = current_timestamp()
        session.call_after_commit(self._run_changed_event, 'run:changed')
        session.call_after_commit(self._run_changed_event, 'run:ended')

    def _run_changed_event(self, topic):
        try:
            Event.create(topic=topic, aspects={'id': self.id})
        except Exception:
            log('exception', 'failed to fire %s event', topic)
        else:
            log('info', 'fired off %s event for %r', topic, self)
