from scheme import *

from flux.engine.rule import RuleList

class Step(Element):
    """A workflow element."""

    schema = Structure({
        'description': Text(),
        'operation': Token(nonempty=True),
        'defaults': Map(Field(), nonnull=True),
        'preoperation': RuleList.schema,
        'postoperation': RuleList.schema,
        'timeout': Integer(),
    }, nonnull=True)


