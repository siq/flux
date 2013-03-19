from scheme import *
from scheme.util import recursive_merge
from spire.schema import NoResultFound
from spire.support.logs import LogHelper
from sqlalchemy import func

from flux.engine.interpolation import Interpolator
from flux.engine.rule import Environment, RuleList
from flux.exceptions import *
from flux.models import Operation, WorkflowExecution

log = LogHelper('flux')

class Step(Element):
    """A workflow element."""

    key_attr = 'name'
    schema = Structure({
        'description': Text(),
        'operation': Token(nonempty=True),
        'parameters': Map(Field(), nonnull=True),
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'timeout': Integer(),
    }, nonnull=True)

    def initiate(self, session, run, ancestor=None, parameters=None, values=None):
        operation = session.query(Operation).get(self.operation)
        if not operation:
            raise UnknownOperationError(self.operation)

        params = {}
        if operation.parameters:
            recursive_merge(params, operation.parameters)
        if self.parameters:
            recursive_merge(params, self.parameters)
        if parameters:
            recursive_merge(params, parameters)

        execution = run.create_execution(session, self.name, ancestor=ancestor)
        session.flush()

        if params:
            interpolator = self._construct_interpolator(run, execution, values)
            params = interpolator.interpolate(operation.schema, params)
        else:
            params = None

        execution.start(params)
        session.commit()

        operation.initiate(id=execution.id, tag=self.name, input=params, timeout=self.timeout)

    def complete(self, session, execution, workflow, output):
        from flux.models import Run
        run = Run.load(session, id=execution.run_id, lockmode='update')

        status = execution.status
        if status != 'completed':
            if status in ('failed', 'timedout'):
                run.complete(session, status)
            return

        interpolator = self._construct_interpolator(run, execution)
        if output:
            #TODO: handle in postoperation
            if output['outcome'] == 'failure':
                execution.status = 'failed'
                run.complete(session, 'failed')
                return
            interpolator['step']['out'] = output

        environment = Environment(workflow, run, interpolator, output, execution)

        postoperation = self.postoperation
        if postoperation:
            postoperation.evaluate(session, environment)
            return

        active_executions = session.query(func.count(WorkflowExecution.id)).filter(
            WorkflowExecution.run_id==run.id,
            WorkflowExecution.status!='completed').scalar()

        if not active_executions:
            run.complete(session, 'completed')

    def _construct_interpolator(self, run=None, execution=None, values=None):
        interpolator = Interpolator()
        if run:
            interpolator.merge(run.contribute_values())
        if execution:
            interpolator.merge(execution.contribute_values())
        if values:
            interpolator.merge(values)
        return interpolator
