from mesh.standard import *
from scheme import *

__all__ = ('Workflow',)

Layout = Sequence(Structure({
    'title': Text(),
    'view': Token(),
    'elements': Sequence(Structure({
        'type': Token(nonempty=True),
        'field': Token(nonempty=True),
        'label': Text(),
        'options': Field(),
    })),
}))

FormStructure = {
    'schema': Definition(nonempty=True),
    'layout': Layout.clone(),
}

class Workflow(Resource):
    """A workflow."""

    name = 'workflow'
    version = 1
    requests = 'create delete get load put query update'

    class schema:
        id = UUID(nonnull=True, oncreate=True, operators='equal')
        name = Text(nonempty=True, operators='equal icontains')
        designation = Token(operators='equal')
        is_service = Boolean(default=False, operators='equal')
        specification = Text(deferred=True)
        form = Structure(FormStructure, deferred=True, readonly=True)
        modified = DateTime(utc=True, readonly=True)

    class create(Resource.create):
        fields = {
            'specification': Text(nonempty=True)
        }
        support_returning = True

    class generate:
        endpoint = ('GENERATE', 'workflow')
        title = 'Generate a workflow specification'
        schema = {
            'name': Text(nonempty=True),
            'description': Text(),
            'schema': Definition(),
            'layout': Layout.clone(),
            'operations': Sequence(Structure({
                'description': Text(),
                'operation': Token(segments=2, nonempty=False),
                'run_params': Field(nonnull=True),
                'step_params': Field(),
            }), min_length=1, nonempty=True),
        }
        responses = {
            OK: Response({
                'name': Text(nonempty=True),
                'specification': Text(nonempty=True),
                'description': Text()
            }),
            INVALID: Response(Errors),
        }

    class update(Resource.update):
        fields = {
            'specification': Text(nonnull=True, min_length=1)
        }
        support_returning = True
