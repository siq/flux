from mesh.standard import bind
from spire.core import Component, Dependency
from spire.mesh import MeshDependency, MeshServer
from spire.runtime import onstartup

import flux.models
from flux.bindings import docket, platoon
from flux.bundles import API
from flux.operations import OPERATIONS
from flux.resources import *

Executor = bind(platoon, 'platoon/1.0/executor')
Registration = bind(docket, 'docket/1.0/registration')

ENTITY_REGISTRATIONS = [
    Registration(
        id='flux:workflow',
        name='workflow',
        title='Workflow',
        specification=API.describe(['workflow']),
    ),
    Registration(
        id='flux:run',
        name='run',
        title='Run',
        specification=API.describe(['run']),
        change_event='run:changed',
        cached_attributes={
            'status': {'type': 'text'},
        },
    ),
]

class Flux(Component):
    api = MeshServer.deploy(bundles=[API])

    docket = MeshDependency('docket')
    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    @onstartup(service='flux')
    def startup_flux(self):
        url = self.flux.url
        for registration in ENTITY_REGISTRATIONS:
            registration.url = url
            registration.put()

        endpoints = {}
        for operation in OPERATIONS.itervalues():
            subject, endpoint = operation().register()
            endpoints[subject] = endpoint

        Executor(id='flux', endpoints=endpoints).put()
