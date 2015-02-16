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
            'promote-products': {
                'products': Map(Text(nonempty=True), Token(nonempty=True), nonempty=True),
            },
            'update-environment': {
                'parameters': Map(Text(nonempty=True), Token(nonempty=True), nonempty=True),
            },
        },
        nonempty=True,
        polymorphic_on='action')

    def execute(self):
        raise NotImplementedError()

class ExecuteStep(Action):
    polymorphic_identity = 'execute-step'

    def execute(self, session, environment):
        if environment.failure:
            return

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

class PromoteProducts(Action):
    polymorphic_identity = 'promote-products'
    interpolation_schema = Map(Surrogate(nonempty=True), Token(nonempty=True))

    def execute(self, session, environment):
        products = environment.interpolator.interpolate(self.interpolation_schema, self.products)
        for token, product in products.iteritems():
            environment.run.associate_product(token, product)

class UpdateEnvironment(Action):
    polymorphic_identity = 'update-environment'
    interpolation_schema = Map(Field(nonempty=True), Token(nonempty=True))

    def execute(self, session, environment):
        parameters = environment.interpolator.interpolate(self.interpolation_schema, self.parameters)
        environment.run.update_environment(parameters)
