from mesh.standard import bind
from scheme import current_timestamp
from spire.mesh import MeshDependency, ModelController, support_returning
from spire.schema import NoResultFound, SchemaDependency

from flux.bindings import platoon, truss
from flux.engine.queue import QueueManager
from flux.models import *
from flux.resources import Run as RunResource

Message = bind(truss, 'truss/1.0/message')
ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')
SubscribedTask = bind(platoon, 'platoon/1.0/subscribedtask')

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

        notify = data.get('notify')
        if notify:
            SubscribedTask.queue_http_task(
                'run-completion',
                self.flux.prepare(
                    'flux/1.0/run', 'task', None,
                    {'task': 'run-completion', 'id': subject.id, 'notify': notify}
                ),
                topic='run:completed', aspects={'id': subject.id})

        if subject.status == 'pending':
            ScheduledTask.queue_http_task('initiate-run',
                self.flux.prepare('flux/1.0/run', 'task', None,
                {'task': 'initiate-run', 'id': subject.id}))

        return subject

    @support_returning
    def update(self, request, response, subject, data):
        if not data:
            return subject

        session = self.schema.session
        if 'name' in data:
            subject.name = data['name']

        status = data['status']
        if status == 'aborted' and subject.is_active:
            subject.initiate_abort(session)
            session.call_after_commit(ScheduledTask.queue_http_task, 'abort-executions',
                self.flux.prepare('flux/1.0/run', 'task', None,
                    {'task': 'abort-executions', 'id': subject.id}))
        elif status == 'pending' and subject.status == 'prepared':
            subject.status = 'pending'
            session.call_after_commit(ScheduledTask.queue_http_task, 'initiate-run',
                self.flux.prepare('flux/1.0/run', 'task', None,
                    {'task': 'initiate-run', 'id': subject.id}))

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
        elif task == 'run-completion':
            self._send_completion_email(subject, data)

    def _annotate_query(self, request, query, data):
        return query.options(joinedload(Run.products))

    def _annotate_resource(self, request, model, resource, data):
        resource['products'] = model.get_products()
        if not data:
            return

        include = data.get('include')
        if include and 'executions' in include:
            attrs = (
                'id', 'execution_id', 'ancestor_id', 'step', 'name',
                'status', 'started', 'ended',
            )
            executions = [e.extract_dict(attrs=attrs) for e in model.executions.all()]
            resource['executions'] = executions

    def _send_completion_email(self, subject, data):
        recipients = [{'to': data['notify'].split(',')}]
        email_subject = 'Workflow run "%s" completed' % subject.name
        body = 'The workflow run "%s" completed and is available for review.' % subject.name
        Message.create(recipients=recipients, subject=email_subject, body=body)
