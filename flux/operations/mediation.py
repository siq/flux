from scheme import *

from flux.operations.operation import *

__all__ = ('MediateSurrogates',)

class MediateSurrogates(Operation):
    """A workflow operation that enables mediation of parameters."""

    id = 'flux:mediate-surrogates'
    endpoint = ('flux/1.0/operation', 'operation')
    operation = {
        'id': 'flux:mediate-surrogates',
        'name': 'Mediate Surrogates',
        'phase': 'operation',
        'schema': Map(key=Token(nonempty=True), value=Structure({
            'surrogate': Surrogate(nonempty=True),
            'mediators': Sequence(Structure({
                'mediator': Object(nonempty=True),
                'arguments': Map(key=Token(nonempty=True), value=Field(nonempty=True)),
            }, nonempty=True), nonempty=True),
        }, nonempty=True), nonempty=True),
        'outcomes': {
            'completed': {
                'outcome': 'success',
                'schema': Map(key=Token(nonempty=True), value=Surrogate(nonempty=True)),
            },
            'failed': {
                'outcome': 'failure',
            },
        },
    }

    def initiate(self, session, data):
        products = {}
        try:
            for token, value in data['input'].iteritems():
                surrogate = value['surrogate']
                for mediator in value['mediators']:
                    self._apply_mediator(surrogate, **mediator)
                products[token] = surrogate
            else:
                return self.outcome('completed', products)
        except Exception:
            return self.outcome('failed')

    def _apply_mediator(self, surrogate, mediator, arguments):
        return mediator(surrogate, **arguments)
