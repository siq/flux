def executing(state=None):
    """Constructs a response for a platoon process executor indicating
    an operation is executing."""

    response = {'status': 'executing'}
    if state:
        response['state'] = state
    return response

def invalidation(*errors):
    """Constructs a response for a platoon process executor representing
    an invalid operation outcome."""

    output = {'status': 'invalid', 'errors': errors}
    return {'status': 'completed', 'output': output}

def outcome(outcome, values=None):
    """Constructs a response for a platoon process executor representing
    a valid operation outcome."""

    output = {'status': 'valid', 'outcome': outcome}
    if values:
        output['values'] = values
    return {'status': 'completed', 'output': output}

class OperationMixin(object):
    """A mixin to support a flux operation implementation."""

    process = None

    def abort(self, session, data):
        pass

    def execute(self, session, response, data):
        status = data['status']
        if status == 'initiating':
            response(self.initiate(session, data))
        elif status == 'executing':
            response(self.report(session, data))
        elif status == 'aborted':
            response(self.abort(session, data))
        elif status == 'timedout':
            response(self.timeout(session, data))

    def initiate(self, session, data):
        pass

    def push(self, id, payload):
        self.process(id=id).update(payload)

    def report(self, session, data):
        pass

    def timeout(self, session, data):
        pass
