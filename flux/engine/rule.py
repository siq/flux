from scheme import *

from flux.engine.action import Action

class Environment(object):
    """A rule evaluation environment."""

    def __init__(self, workflow, run, interpolator, output=None, ancestor=None):
        self.ancestor = ancestor
        self.interpolator = interpolator
        self.output = output
        self.run = run
        self.workflow = workflow

class Condition(Element):
    """A rule condition."""

    #schema = Union(Text(nonempty=True), Map(Field(), nonempty=True),
    #    name='condition')
    schema = Map(Field(), nonnull=True, name='condition')

class Rule(Element):
    """A workflow rule."""

    schema = Structure({
        'description': Text(),
        'condition': Condition.schema,
        'actions': Sequence(Action.schema, nonnull=True),
        'terminal': Boolean(nonnull=True, default=False),
    })

    def evaluate(self, session, environment):
        condition = self.condition
        if not condition:
            return True

        return True

    def execute(self, session, environment):
        actions = self.actions
        if not actions:
            return

        for action in actions:
            action.execute(session, environment)

class RuleList(Element):
    """A workflow rule list."""

    schema = Sequence(Rule.schema, name='rules', nonnull=True)

    def evaluate(self, session, environment):
        for rule in self.rules:
            if rule.evaluate(session, environment):
                rule.execute(session, environment)
                if rule.terminal:
                    break
