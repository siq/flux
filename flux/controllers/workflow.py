from spire.mesh import ModelController
from spire.schema import SchemaDependency

from flux.models import *
from flux.resources import Workflow as WorkflowResource

class WorkflowController(ModelController):
    resource = WorkflowResource
    version = (1, 0)

    model = Workflow
    mapping = 'id name designation specification modified'
    schema = SchemaDependency('flux')
