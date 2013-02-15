from mesh.standard import bind
from spire.core import Unit
from spire.mesh import MeshDependency
from spire.schema import SchemaDependency

from flux.bindings import platoon
from flux.models import Operation

Process = bind(platoon, 'platoon/1.0/process')
Queue = bind(platoon, 'platoon/1.0/queue')

class QueueManager(Unit):
    """The queue manager."""

    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')
    schema = SchemaDependency('flux')

    def bootstrap(self):
        session = self.schema.session
        for operation in session.query(Operation):
            self._register_queue(operation)

    def initiate(self, operation, tag, input=None, id=None, timeout=None):
        params = {'queue_id': operation.queue_id, 'tag': tag}
        if id is not None:
            params['id'] = id
        if input is not None:
            params['input'] = input
        if timeout is not None:
            params['timeout'] = timeout

        Process.create(**params)

    def register(self, operation):
        self._register_queue(operation)

    def _register_queue(self, operation):
        endpoint = self.flux.prepare('flux/1.0/operation', 'process', operation.id,
            preparation={'type': 'http'})

        Queue(id=operation.queue_id, subject=operation.id, name=operation.name,
            endpoint=endpoint).put()
