from docket.surrogates import entity
from scheme import *

from flux.constants import *

class request(entity):
    """A scheme surrogate for requests."""

    schema = entity.schema.extend({
        'status': Enumeration(REQUEST_STATUSES, nonempty=True),
    })

    @classmethod
    def contribute(cls, value):
        value['entity'] = 'flux:request'
        super(request, cls).contribute(value)

class run(entity):
    """A scheme surrogate for workflow runs."""

    schema = entity.schema.extend({
        'status': Enumeration(RUN_STATUSES, nonempty=True),
    })

    @classmethod
    def contribute(cls, value):
        value['entity'] = 'flux:run'
        super(run, cls).contribute(value)
