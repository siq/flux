from mesh.standard import bind
from scheme import current_timestamp
from spire.mesh import MeshDependency, ModelController, support_returning
from spire.schema import NoResultFound, SchemaDependency

from flux.bindings import platoon
from flux.engine.queue import QueueManager
from flux.models import *
from flux.resources import Run as RunResource

ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')

class RunController(ModelController):
    resource = RunResource
    version = (1, 0)

    model = Run
    mapping = 'id workflow_id name status parameters started ended'
    schema = SchemaDependency('flux')

    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    @support_returning
    def create(self, request, response, subject, data):
        session = self.schema.session
        subject = self.model.create(session, **data)

        session.commit()
        ScheduledTask.queue_http_task('initiate-run',
            self.flux.prepare('flux/1.0/run', 'task', None,
            {'task': 'initiate-run', 'id': subject.id}))

        return subject

    @support_returning
    def update(self, request, response, subject, data):
        session = self.schema.session

        status = data.pop('status')
        if status == 'aborted' and subject.status in ('active', 'pending', 'waiting'):
            subject._end_run(session, 'aborted')
            ScheduledTask.queue_http_task('abort-run',
                self.flux.prepare('flux/1.0/run', 'task', None,
                {'task': 'abort-executions', 'id': subject.id}))

        session.commit()
        return subject

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

        elif task == 'abort-executions':
            subject.abort_executions(session)
            session.commit()

    def _annotate_resource(self, request, model, resource, data):
        if data and 'include' in data and 'executions' in data['include']:
            attrs = ('id', 'execution_id', 'ancestor_id', 'step', 'name',
                     'status', 'started', 'ended',)
            executions = [e.extract_dict(attrs=attrs) for e in model.executions]
            resource['executions'] = executions
