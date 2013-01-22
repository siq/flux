from scheme import *

__all__ = ('Element',)

class ElementMeta(type):
    def __new__(metatype, name, bases, namespace):
        element = type.__new__(metatype, name, bases, namespace)
        if element.schema is None:
            return element

        schema = element.schema
        if isinstance(schema, Structure):
            element._instance_attrs = schema.generate_default(sparse=False)
        elif schema.name:
            element._instance_attrs = {schema.name: schema.default}
        else:
            raise Exception()

        schema.instantiator = element.__instantiate__
        schema.extractor = element.__extract__
        return element

class Element(object):
    """An workflow element."""

    __metaclass__ = ElementMeta
    schema = None

    def __init__(self, **params):
        for attr, default in self._instance_attrs.iteritems():
            setattr(self, attr, params.get(attr, default))

    def __repr__(self):
        aspects = []
        for attr in ('id', 'name', 'title'):
            value = getattr(self, attr, None)
            if value is not None:
                aspects.append('%s=%r' % (attr, value))
        return '%s(%s)' % (type(self).__name__, ', '.join(aspects))

    @classmethod
    def __extract__(cls, field, subject):
        if isinstance(field, Structure):
            return subject.__dict__
        else:
            return getattr(subject, field.name)

    @classmethod
    def __instantiate__(cls, field, value, key=None):
        if isinstance(field, Structure):
            return cls(**value)
        else:
            return cls(**{field.name: value})

    def serialize(self, format='yaml'):
        return self.schema.serialize(self.schema.extract(self), format)

    @classmethod
    def unserialize(cls, value, format='yaml'):
        return cls.schema.instantiate(cls.schema.unserialize(value, format))
