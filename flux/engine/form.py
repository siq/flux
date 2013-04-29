from mesh.exceptions import OperationError
from scheme import *

def reverse_enumerate(iterable, start=0):
    iterator = reversed(iterable)
    for enum, val in enumerate(iterator):
        yield start - enum, val

class Form(Element):
    """A workflow form."""

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
        layout = self.layout
        fields = self.schema.clone().structure
        elements = reduce(lambda x, y: x + y, [l['elements']  for l in layout])

        for i, element in reverse_enumerate(elements[:], len(elements) - 1):
            if fields.pop(element['field'], False):
                elements.pop(i)

        errors = {}
        for element in elements:
            errors[element['field']] = OperationError(token='no-matching-schema-field')

        for field in fields.iterkeys():
            errors[field] = OperationError(token='no-matching-layout-element')

        if errors:
             raise OperationError(structure=errors)
