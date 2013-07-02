from mesh.standard import bind
from spire.core import Unit
from spire.mesh import MeshDependency

from flux.bindings import docket, platoon
from flux.support.operation import *

__all__ = ('Operation', 'ScheduledTask', 'SubscribedTask')

Process = bind(platoon, 'platoon/1.0/process')
ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')
SubscribedTask = bind(platoon, 'platoon/1.0/subscribedtask')

class Operation(Unit, OperationMixin):
    """A workflow operation."""

    docket = MeshDependency('docket')
    docket_entity = MeshDependency('docket.entity')
    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    process = Process

    id = None
    endpoint = None

    def register(self):
        bind('flux.API', 'flux/1.0/operation')(**self.operation).put()
        return self.id, self.flux.prepare(*self.endpoint, preparation={'type': 'http'})
