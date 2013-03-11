from mesh.standard import bind
from spire.core import Unit
from spire.mesh import MeshDependency

from flux.bindings import docket, platoon

__all__ = ('Operation', 'Process', 'ScheduledTask', 'SubscribedTask')

Process = bind(platoon, 'platoon/1.0/process')
ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')
SubscribedTask = bind(platoon, 'platoon/1.0/subscribedtask')

class Operation(Unit):
    """A workflow operation."""

    docket = MeshDependency('docket')
    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    def abort(self, session, data):
        pass

    def execute(self, session, response, data):
        status = data['status']
        if status == 'initiating':
            response(self.initiate(session, data))
        elif status == 'executing':
            response(self.report(session, data))
        elif status == 'aborted':
            response(self.abort(session, data))
        elif status == 'timedout':
            response(self.timeout(session, data))

    def initiate(self, session, data):
        pass

    def push(self, id, status=None, output=None, progress=None, state=None):
        payload = {}
        if status:
            payload['status'] = status
        if output:
            payload['output'] = output
        if progress:
            payload['progress'] = progress
        if state:
            payload['state'] = state

        Process(id=id).update(payload)

    def register(self):
        from flux.bundles import API
        Operation = bind(API, 'flux/1.0/operation')

        Operation(**self.operation).put()
        return self.id, self.flux.prepare(*self.endpoint, preparation={'type': 'http'})

    def report(self, session, data):
        pass

    def timeout(self, session, data):
        pass
