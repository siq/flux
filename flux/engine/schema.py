from scheme import *

from flux.engine.step import Step

Rule = Structure({
    'description': Text(),
    'condition': Text(),
    'actions': Sequence(Structure({
        'action': Token(segments=2, nonempty=True),
    }, nonnull=True), nonnull=True),
    'terminal': Boolean(nonnull=True, default=False),
})

Step = Structure({
    'description': Text(),
    'operation': Token(nonempty=True),
    'defaults': Map(Text(), nonnull=True),
    'prerules': Sequence(Rule, nonnull=True),
    'postrules': Sequence(Rule, nonnull=True),
    'timeout': Integer(),
}, nonnull=True, instantiator=Step, extractor=Step)

Workflow = Structure({
    'name': Text(nonempty=True),
    'description': Text(),
    'steps': Map(Step, nonempty=True),
})
