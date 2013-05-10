from scheme import *

from flux.engine.interpolation import Interpolator
from flux.models import Operation

class Action(Element):
    """A workflow action."""

    schema = Structure(
        structure={
            'execute-operation': {
                'operation': Token(nonempty=True),
                'parameters': Field(),
            },
            'execute-step': {
                'step': Token(nonempty=True),
                'parameters': Field(),
            },
            'ignore-step-failure': {
            },
        },
        nonempty=True,
        polymorphic_on='action')

    def execute(self):
        raise NotImplementedError()

class ExecuteStep(Action):
    polymorphic_identity = 'execute-step'

    def execute(self, session, environment):
        workflow = environment.workflow
        try:
            step = workflow.steps[self.step]
        except KeyError:
            raise

        values = {'step': {'out': environment.output}}
        step.initiate(session, environment.run, environment.ancestor,
            self.parameters, values)

class IgnoreStepFailure(Action):
    polymorphic_identity = 'ignore-step-failure'

    def execute(self, session, environment):
        environment.failure = False
