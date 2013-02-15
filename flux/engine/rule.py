from scheme import *

from flux.engine.action import Action

class Condition(Element):
    """A rule condition."""

    #schema = Union(Text(nonempty=True), Map(Field(), nonempty=True),
    #    name='condition')
    schema = Map(Field(), nonempty=True, name='condition')

class Rule(Element):
    """A workflow rule."""

    schema = Structure({
        'description': Text(),
        'condition': Condition.schema,
        'actions': Sequence(Action.schema, nonnull=True),
        'terminal': Boolean(nonnull=True, default=False),
    })

class RuleList(Element):
    """A workflow rule list."""

    schema = Sequence(Rule.schema, name='rules', nonnull=True)

    def evaluate(self):
        for rule in self.rules:
            pass
