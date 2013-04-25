from copy import deepcopy
from mesh.exceptions import OperationError
from scheme import *

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
    }, nonnull=True)

    def extract_dict(self):
        schema = self.__class__.schema
        return self.extract(schema, self)

    def verify(self):
        layout = deepcopy(self.layout)
        fields = deepcopy(self.schema.structure)
        elements = reduce(lambda x, y: x + y, [l['elements']  for l in layout])

        for i, element in enumerate(elements[:]):
            if fields.pop(element['field'], False):
                elements.pop(i)

        errors = {}
        for element in elements:
            errors[element['field']] = OperationError(token='no-field-layout')

        for field in fields.iterkeys():
            errors[field] = OperationError(token='no-element-schema')

        if errors:
             raise OperationError(structure=errors)
