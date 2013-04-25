from copy import copy, deepcopy
from mesh.exceptions import OperationError
from scheme import *

def reverse_enumerate(iterable, start=0):
    iterator = reversed(iterable)
    for enum, val in enumerate(iterator):
        yield start - enum, val

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

        for i, element in reverse_enumerate(elements[:], len(elements) - 1):
            if fields.pop(element['field'], False):
                elements.pop(i)

        errors = {}
        for element in elements:
            errors[element['field']] = OperationError(token='no-field-layout')

        for field in fields.iterkeys():
            errors[field] = OperationError(token='no-element-schema')

        if errors:
             raise OperationError(structure=errors)
