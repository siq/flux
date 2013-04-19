from mesh.exceptions import GoneError
from mesh.standard import bind
from spire.mesh import ModelController, MeshDependency
from spire.schema import SchemaDependency

from flux.models import WorkflowExecution as WorkflowExecutionModel
from flux.resources import Execution

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

        status = data.pop('status')
        if status == 'aborted' and subject.status in ('active', 'pending', 'waiting'):
            subject.abort(session)
            session.commit()

            Run = self.flux.bind('flux/1.0/run')
            run = Run.get(subject.run_id)
            run.update({'status': 'aborted'})

        response({'id': subject.id})
