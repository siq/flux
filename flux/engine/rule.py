from mesh.exceptions import OperationError
from scheme import *

from flux.engine.action import Action

class Environment(object):
    """A rule evaluation environment."""

    def __init__(self, workflow, run, interpolator, output=None, ancestor=None,
                 failure=False):
        self.ancestor = ancestor
        self.failure = failure
        self.interpolator = interpolator
        self.output = output
        self.run = run
        self.workflow = workflow

class Condition(Element):
    """A rule condition."""

    schema = Text(nonnull=True, name='condition')

    def evaluate(self, session, environment):
        return environment.interpolator.evaluate(self.condition)

class Rule(Element):
    """A workflow rule."""

    schema = Structure({
        'description': Text(),
        'condition': Condition.schema,
        'actions': Sequence(Action.schema, nonnull=True),
        'terminal': Boolean(nonnull=True, default=False),
    }, key_order='description condition actions terminal')

    def evaluate(self, session, environment):
        condition = self.condition
        if condition:
            return condition.evaluate(session, environment)
        else:
            return True

    def execute(self, session, environment):
        actions = self.actions
        if not actions:
            return

        for action in actions:
            action.execute(session, environment)

    def verify(self, steps):
        for action in self.actions:
            if action.action == 'execute-step':
                if action.step not in steps:
                    raise OperationError('invalid-execute-step')

class RuleList(Element):
    """A workflow rule list."""

    schema = Sequence(Rule.schema, name='rules', nonnull=True)

    def evaluate(self, session, environment):
        for rule in self.rules:
            if rule.evaluate(session, environment):
                rule.execute(session, environment)
                if rule.terminal:
                    break

    def verify(self, steps):
        for rule in self.rules:
            rule.verify(steps)
