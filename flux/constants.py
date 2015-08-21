OPERATION_PHASES = 'operation preoperation postoperation prerun postrun'

ACTIVE_RUN_STATUSES = 'aborting active pending suspended waiting'
RUN_STATUSES = 'aborted aborting active completed failed invalidated pending prepared suspended timedout waiting'

REQUEST_STATUSES = 'canceled claimed completed declined done reopened pending prepared failed'

#this is dummy specification for persistence of mule flow into flux/workflow table
MULE_DUMMY_SPEC = 'name: mule dummy workflow\n' + 'entry: step1\n' + 'steps:\n' + '  step1:\n' + '    operation: flux:test-operation'

MULE_DEPLOY_URL = 'http://localhost:8082/deploy'

MULE_UNDEPLOY_URL = 'http://localhost:8082/undeploy'

ENDPOINT_URL_PREFIX = 'http://localhost:8081/'