from mesh.exceptions import OperationError
from scheme import *

from flux.engine.interpolation import Interpolator
from flux.models import Operation

class Parameter(Element):
    """A workflow parameter."""

    schema = Structure({
        'schema': Definition(),
        'layout': Sequence(Structure({
            'title': Text(),
            'elements': Sequence(Structure({
                'type': Token(nonempty=True),
                'field': Token(nonempty=True),
                'label': Text(),
                'options': Field(),
            })),
        })),
    })

    def verify(self):
        layout = self.layout
        schema = self.schema
        elements = reduce(lambda x,y: x+y, [l['elements']  for l in layout])
        fields = {field.name: field for field in schema.structure.itervalues()}

        while elements and fields:
            element = elements.pop()
            fields.pop(element['field'])

        # TODO: elaborate
        if elements:
            raise OperationError(token='some error')

        if fields:
            raise OperationError(token='some error')
