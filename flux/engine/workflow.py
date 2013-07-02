from mesh.exceptions import OperationError
from scheme import *
from spire.support.logs import LogHelper

from flux.engine.form import Form
from flux.engine.product import Product
from flux.engine.rule import RuleList
from flux.engine.step import Step
from flux.exceptions import *

log = LogHelper('flux')

class Workflow(Element):
    """A workflow plan."""

    schema = Structure({
        'name': Text(nonempty=True),
        'entry': Token(nonempty=True),
        'form': Form.schema,
        'products': Map(Product.schema, Token(nonempty=True), nonnull=True),
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'prerun': RuleList.schema,
        'postrun': RuleList.schema,
        'steps': Map(Step.schema, Token(nonempty=True), nonnull=True),
    }, key_order='name entry form products prerun postrun preoperation postoperation steps')

    def initiate(self, session, run):
        log('info', 'initiating %r', run)
        try:
            self.steps[self.entry].initiate(session, run)
        except Exception:
            log('exception', 'initiation of %r failed due to exception', run)
            run.fail(session)

    def verify(self):
        steps = self.steps

        if self.entry not in steps:
            raise OperationError(token='invalid-entry-step')

        if self.form:
            self.form.verify()

        for rulelist in ('preoperation', 'postoperation', 'prerun', 'postrun'):
            element = getattr(self, rulelist, None)
            if element:
                element.verify(steps)

        for step in steps.itervalues():
            step.verify(steps)
