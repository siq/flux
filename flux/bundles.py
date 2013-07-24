from mesh.standard import Bundle, mount

from flux.resources import *

API = Bundle('flux',
    mount(Execution, 'flux.controllers.execution.ExecutionController'),
    mount(Message, 'flux.controllers.message.MessageController'),    
    mount(Operation, 'flux.controllers.operation.OperationController'),
    mount(Request, 'flux.controllers.request.RequestController'),
    mount(Run, 'flux.controllers.run.RunController'),
    mount(Workflow, 'flux.controllers.workflow.WorkflowController'),
    mount(Request, 'flux.controllers.request.RequestController'),
    mount(Message, 'flux.controllers.message.MessageController'),
)
