from mesh.exceptions import OperationError
from scheme import *
from spire.support.logs import LogHelper

from flux.engine.parameter import Parameter
from flux.engine.rule import RuleList
from flux.engine.step import Step
from flux.exceptions import *

log = LogHelper('flux')

class Workflow(Element):
    """A workflow plan."""

    schema = Structure({
        'name': Text(nonempty=True),
        'parameters': Parameter.schema,
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'prerun': RuleList.schema,
        'postrun': RuleList.schema,
        'steps': Map(Step.schema, nonnull=True),
        'entry': Token(nonempty=True),
    }, key_order='name parameters entry prerun postrun preoperation postoperation steps')

    def initiate(self, session, run):
        log('info', 'initiating %r', run)
        try:
            self.steps[self.entry].initiate(session, run)
        except Exception:
            log('exception', 'initiation of %r failed due to exception', run)
            run.complete(session, 'failed')

    def verify(self):
        steps = self.steps

        if self.entry not in steps:
            raise OperationError(token='invalid-entry-step')

        if self.parameters:
            self.parameters.verify()

        for rulelist in ('preoperation', 'postoperation', 'prerun', 'postrun'):
            element = getattr(self, rulelist, None)
            if element:
                element.verify(steps)
                
        for step in steps.itervalues():
            step.verify(steps)
