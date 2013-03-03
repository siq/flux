from mesh.exceptions import GoneError
from mesh.standard import bind
from spire.mesh import ModelController, MeshDependency
from spire.schema import SchemaDependency

from flux.bindings import platoon
from flux.models import WorkflowExecution as WorkflowExecutionModel
from flux.resources import Execution

Process = bind(platoon, 'platoon/1.0/process')

class ExecutionController(ModelController):
    """A step execution controller"""

    model = WorkflowExecutionModel
    resource = Execution
    schema = SchemaDependency('flux')
    version = (1, 0)

    platoon = MeshDependency('platoon')

    def update(self, request, response, subject, data):
        subject.update_with_mapping(**data)
        self.schema.session.commit()

        try:
            process = Process.get(subject.id)
        except GoneError:
            pass
        else:
            process.update(None, status=subject.status)

        response({'id': subject.id})
