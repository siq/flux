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
        if not run.is_active:
            return

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

        interpolator = self._construct_interpolator(run, execution, values)
        if params:
            params = interpolator.interpolate(operation.schema, params)
        else:
            params = None

        workflow = run.workflow.workflow
        environment = Environment(workflow, run, interpolator, output=values,
                                  ancestor=execution)
        preoperation = self.preoperation
        if preoperation:
            try:
                preoperation.evaluate(session, environment)
            except Exception:
                log('exception',
                    'preoperation for %r encountered an exception', self)
                self.run.fail(session)

        execution.start(params)
        session.commit()

        operation.initiate(id=execution.id, tag=self.name, input=params, timeout=self.timeout)

    def process(self, session, execution, workflow, status, output):
        from flux.models import Run
        run = Run.load(session, id=execution.run_id, lockmode='update')

        failure = False
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
            failure = True
            execution.fail(session)
        elif status == 'timedout':
            failure = True
            execution.timeout(session)

        interpolator = self._construct_interpolator(run, execution)
        if values:
            interpolator['step']['out'] = values

        environment = Environment(workflow, run, interpolator, output=values,
                                  ancestor=execution, failure=failure)

        postoperation = self.postoperation
        if postoperation:
            try:
                postoperation.evaluate(session, environment)
            except Exception:
                log('exception',
                    'postoperation for %r encountered an exception', self)
                self.run.fail(session)

        if environment.failure:
            if execution.status == 'failed':
                return run.fail(session)
            if execution.status == 'timedout':
                return run.timeout(session)

        if not run.active_executions.count():
            executions = run.executions
            execution_status = WorkflowExecution.status

            if executions.filter(execution_status=='failed').count():
                return run.fail(session)
            if executions.filter(execution_status=='timedout').count():
                return run.timeout(session)
            if not executions.filter(execution_status!='completed').count():
                return run.complete(session)

    def verify(self, steps):
        for rulelist in ('preoperation', 'postoperation'):
            element = getattr(self, rulelist, None)
            if element:
                element.verify(steps)

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

