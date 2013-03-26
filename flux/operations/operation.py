from mesh.standard import bind
from spire.core import Unit
from spire.mesh import MeshDependency

from flux.bindings import docket, platoon
from flux.support.operation import *

__all__ = ('Operation', 'Process', 'ScheduledTask', 'SubscribedTask', 'executing',
    'invalidation', 'outcome')

Process = bind(platoon, 'platoon/1.0/process')
ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')
SubscribedTask = bind(platoon, 'platoon/1.0/subscribedtask')

class Operation(Unit, OperationMixin):
    """A workflow operation."""

    docket = MeshDependency('docket')
    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    process = Process

    def register(self):
        from flux.bundles import API
        Operation = bind(API, 'flux/1.0/operation')

        Operation(**self.operation).put()
        return self.id, self.flux.prepare(*self.endpoint, preparation={'type': 'http'})
