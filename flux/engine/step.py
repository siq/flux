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

        execution = run.create_execution(session, self.name, ancestor=ancestor,
                name=operation.name)
        session.flush()

        if params:
            interpolator = self._construct_interpolator(run, execution, values)
            params = interpolator.interpolate(operation.schema, params)
        else:
            params = None

        execution.start(params)
        session.commit()

        operation.initiate(id=execution.id, tag=self.name, input=params, timeout=self.timeout)

    def process(self, session, execution, workflow, status, output):
        from flux.models import Run
        run = Run.load(session, id=execution.run_id, lockmode='update')

        values = None
        operation = session.query(Operation).get(self.operation)

        if status == 'completed':
            if output['status'] == 'valid':
                status, outcome, values = self._parse_outcome(operation, output)
                if status == 'completed':
                    execution.complete(session, outcome)
                else:
                    execution.fail(session, outcome)
            elif output['status'] == 'invalid':
                execution.invalidate(session, output['errors'])
                return run.invalidate(session)
        elif status == 'failed':
            execution.fail(session)
        elif status == 'timedout':
            execution.timeout(session)

        # temporary hack
        if execution.status == 'failed':
            return run.fail(session)
        elif execution.status == 'timedout':
            return run.timeout(session)

        interpolator = self._construct_interpolator(run, execution)
        if values:
            interpolator['step']['out'] = values

        environment = Environment(workflow, run, interpolator, values, execution)

        postoperation = self.postoperation
        if postoperation:
            postoperation.evaluate(session, environment)
            return

        active_executions = session.query(func.count(WorkflowExecution.id)).filter(
            WorkflowExecution.run_id==run.id,
            WorkflowExecution.status!='completed').scalar()

        if not active_executions:
            run.complete(session)

    def _construct_interpolator(self, run=None, execution=None, values=None):
        interpolator = Interpolator()
        if run:
            interpolator.merge(run.contribute_values())
        if execution:
            interpolator.merge(execution.contribute_values())
        if values:
            interpolator.merge(values)
        return interpolator

    def _parse_outcome(self, operation, output):
        try:
            outcome = operation.outcomes[output['outcome']]
        except KeyError:
            raise # todo: handle this properly

        values = output.get('values')
        if values:
            pass # todo: validate using schema here
        else:
            values = {}

        status = ('completed' if outcome.outcome == 'success' else 'failed')
        return status, outcome.name, values

