from scheme import *

class Product(Element):
    """A workflow product."""

    key_attr = 'token'
    schema = Structure({
        'surrogate': Token(nonempty=True),
    })
