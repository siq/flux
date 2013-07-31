from docket.surrogates import entity
from scheme import *

from flux.constants import *

class request(entity):
    """A scheme surrogate for requests."""

    schemas = (
        entity.schemas[0].extend({
            'status': Enumeration(REQUEST_STATUSES, nonempty=True),
        }),
    )

    @classmethod
    def contribute(cls, value, version):
        value['entity'] = 'flux:request'
        super(request, cls).contribute(value, version)

class run(entity):
    """A scheme surrogate for workflow runs."""

    schemas = (
        entity.schemas[0].extend({
            'status': Enumeration(RUN_STATUSES, nonempty=True),
        }),
    )

    @classmethod
    def contribute(cls, value, version):
        value['entity'] = 'flux:run'
        super(run, cls).contribute(value, version)
