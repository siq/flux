from mesh.standard import bind
from spire.mesh import MeshDependency, ModelController
from spire.schema import NoResultFound, SchemaDependency

from flux.bindings import platoon
from flux.models import *
from flux.resources import Run as RunResource

ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')

class RunController(ModelController):
    resource = RunResource
    version = (1, 0)

    model = Run
    mapping = 'id workflow_id name status started ended'
    schema = SchemaDependency('flux')

    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)

        session.commit()
        ScheduledTask.queue_http_task('initiate-run',
            self.flux.prepare('flux/1.0/run', 'task', None,
            {'task': 'initiate-run', 'id': subject.id}))

        response({'id': subject.id})

    def task(self, request, response, subject, data):
        session = self.schema.session
        if 'id' in data:
            try:
                subject = self.model.load(session, id=data['id'], lockmode='update')
            except NoResultFound:
                return

        task = data['task']
        if task == 'initiate-run':
            subject.initiate(session)
            session.commit()
