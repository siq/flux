from mesh.exceptions import GoneError
from mesh.standard import bind
from spire.mesh import ModelController, MeshDependency
from spire.schema import SchemaDependency

from flux.bindings import platoon
from flux.models import WorkflowExecution as WorkflowExecutionModel
from flux.resources import Execution

ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')

class ExecutionController(ModelController):
    """A step execution controller"""

    model = WorkflowExecutionModel
    resource = Execution
    schema = SchemaDependency('flux')
    version = (1, 0)

    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')

    def update(self, request, response, subject, data):
        session = self.schema.session
        task = subject.update(session, **data)
        if task == 'abort':
            subject.initiate_abort(session)
            session.call_after_commit(ScheduledTask.queue_http_task, 'abort-run',
                self.flux.prepare('flux/1.0/execution', 'task', None,
                    {'task': 'abort-run', 'id': subject.id}))

        session.commit()
        response({'id': subject.id})

    def task(self, request, response, subject, data):
        session = self.schema.session
        if 'id' in data:
            try:
                subject = self.model.load(session, id=data['id'], lockmode='update')
            except NoResultFound:
                return

        task = data['task']
        if task == 'abort-run':
            subject.run.abort_executions(session)
            session.commit()
