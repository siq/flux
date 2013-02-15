from scheme import *

class Condition(Element):
    """A workflow rule condition."""


class Rule(Element):
    """A workflow rule."""

    schema = Structure({
        'description': Text(),
        'condition': Field(),
        'actions': Sequence(Structure({
            'action': Token(segments=2, nonempty=True),
        }, nonnull=True), nonnull=True),
        'terminal': Boolean(nonnull=True, default=False),
    })

class RuleList(Element):
    """A workflow rule list."""

    schema = Sequence(Rule.schema, name='rules', nonnull=True)

    def evaluate(self):
        for rule in self.rules:
            pass
