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

    platoon = MeshDependency('platoon')
    docket_entity = MeshDependency('docket.entity')

    def update(self, request, response, subject, data):
        session = self.schema.session
        subject.update_with_mapping(**data)
        session.commit()

        if subject.status == 'aborted':
            subject.abort(session)
            Run = self.docket_entity.bind('docket.entity/1.0/flux/1.0/run')
            run = Run.get(subject.run_id)
            run.update({'status': 'aborted'})

        response({'id': subject.id})
