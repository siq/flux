from scheme import *
from spire.support.logs import LogHelper

from flux.engine.rule import RuleList
from flux.engine.step import Step
from flux.exceptions import *

log = LogHelper('flux')

class Workflow(Element):
    """A workflow plan."""

    schema = Structure({
        'name': Text(nonempty=True),
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'prerun': RuleList.schema,
        'postrun': RuleList.schema,
        'steps': Map(Step.schema, nonnull=True),
        'entry': Token(nonempty=True),
    }, key_order='name entry prerun postrun preoperation postoperation steps')

    def initiate(self, session, run):
        log('info', 'initiating %r', run)
        try:
            self.steps[self.entry].initiate(session, run)
        except Exception:
            log('exception', 'initiation of %r failed due to exception', run)
            run.complete(session, 'failed')
