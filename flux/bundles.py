from mesh.standard import Bundle, mount

from flux.resources import *

API = Bundle('flux',
    mount(Operation, 'flux.controllers.operation.OperationController'),
)
