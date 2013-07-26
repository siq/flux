from mesh.exceptions import OperationError
from scheme import *
from spire.support.logs import LogHelper

from flux.engine.product import Product
from flux.engine.rule import RuleList
from flux.engine.step import Step
from flux.exceptions import *

log = LogHelper('flux')

Layout = Sequence(Structure({
    'title': Text(),
    'elements': Sequence(Structure({
        'type': Token(nonempty=True),
        'field': Token(nonempty=True),
        'label': Text(),
        'options': Field(),
    })),
}))

def reverse_enumerate(iterable, start=0):
    iterator = reversed(iterable)
    for enum, val in enumerate(iterator):
        yield start - enum, val

class Workflow(Element):
    """A workflow plan."""

    schema = Structure({
        'name': Text(nonempty=True),
        'entry': Token(nonempty=True),
        'parameters': Map(Field(nonempty=True), Token(nonempty=True)),
        'schema': Definition(),
        'layout': Layout,
        'products': Map(Product.schema, Token(nonempty=True), nonnull=True),
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'prerun': RuleList.schema,
        'postrun': RuleList.schema,
        'steps': Map(Step.schema, Token(nonempty=True), nonnull=True),
    }, key_order='name entry parameters schema layout products prerun postrun preoperation postoperation steps')

    def initiate(self, session, run):
        log('info', 'initiating %r', run)
        self.steps[self.entry].initiate(session, run)

    def verify(self):
        steps = self.steps

        if self.entry not in steps:
            raise OperationError(token='invalid-entry-step')

        if self.layout:
            self._verify_layout(self.layout, self.schema)

        for rulelist in ('preoperation', 'postoperation', 'prerun', 'postrun'):
            element = getattr(self, rulelist, None)
            if element:
                element.verify(steps)

        for step in steps.itervalues():
            step.verify(steps)

    @classmethod
    def _verify_layout(cls, layout, schema):
        fields = schema.clone().structure
        elements = reduce(lambda x, y: x + y, [l['elements'] for l in layout])

        for i, element in reverse_enumerate(elements[:], len(elements) - 1):
            if fields.pop(element['field'], False):
                elements.pop(i)
        if elements or fields:
            raise OperationError(token='unknown-layout-elements')
