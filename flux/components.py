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
Intent = bind(docket, 'docket/1.0/intent')
Registration = bind(docket, 'docket/1.0/registration')
SubscribedTask = bind(platoon, 'platoon/1.0/subscribedtask')

ENTITY_REGISTRATIONS = [
    Registration(
        id='flux:workflow',
        name='workflow',
        title='Workflow',
        specification=API.describe(['workflow']),
        cached_attributes={
            'is_service': {'type': 'boolean'},
            'type': {'type': 'text'},
        },
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
    Registration(
        id='flux:request',
        name='request',
        title='Request',
        specification=API.describe(['request']),
        change_event='request:changed',
        cached_attributes={
            'status': {'type': 'text'},
            'assignee': {'type': 'text'},
            'completed': {'type': 'datetime'},
            'claimed': {'type': 'datetime'},
        }
    ),
]

GENERATED_BY = Intent(
    id='generated-by',
    name='Generated by',
    exclusive=True)

REASSIGN_REQUEST_ASSIGNEE = SubscribedTask(
    id='d2407ce4-dcda-4859-bba7-e73741041e5c',
    tag='reassign-request-assignee',
    topic='subject:deleted',
    aspects={'entity': 'bastion:subject'})

class Flux(Component):
    api = MeshServer.deploy(bundles=[API])

    docket = MeshDependency('docket')
    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')
    truss = MeshDependency('truss')

    @onstartup(service='flux')
    def startup_flux(self):
        GENERATED_BY.put()

        url = self.flux.url
        for registration in ENTITY_REGISTRATIONS:
            registration.url = url
            registration.put()

        endpoints = {}
        for operation in OPERATIONS.itervalues():
            subject, endpoint = operation().register()
            endpoints[subject] = endpoint

        Executor(id='flux', endpoints=endpoints).put()

        REASSIGN_REQUEST_ASSIGNEE.set_http_task(
            self.flux.prepare('flux/1.0/request', 'task', None,
            {'task': 'reassign-request-assignee'},
            preparation={'injections': ['event']}))
        REASSIGN_REQUEST_ASSIGNEE.put()
