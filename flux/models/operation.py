from mesh.standard import bind
from spire.core import Unit
from spire.mesh import Definition, MeshDependency
from spire.schema import *
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.bindings import platoon
from flux.constants import *

Process = bind(platoon, 'platoon/1.0/process')
Queue = bind(platoon, 'platoon/1.0/queue')

schema = Schema('flux')

class Operation(Model):
    """A workflow operation."""

    class meta:
        schema = schema
        tablename = 'operation'

    id = Token(segments=2, nullable=False, primary_key=True)
    name = Text(nullable=False)
    phase = Enumeration(OPERATION_PHASES, nullable=False)
    description = Text()
    schema = Definition()

    outcomes = relationship('Outcome', backref='operation',
        collection_class=attribute_mapped_collection('name'),
        cascade='all,delete-orphan', passive_deletes=True)

    @property
    def queue_id(self):
        return 'flux-operation:%s' % self.id

    @classmethod
    def create(cls, session, outcomes, **attrs):
        operation = cls(**attrs)
        
        for name, outcome in outcomes.iteritems():
            outcome = Outcome(name=name, **outcome)
            operation.outcomes[name] = outcome

        session.add(operation)
        return operation

class Outcome(Model):
    """An operation outcome."""

    class meta:
        constraints = [UniqueConstraint('operation_id', 'name')]
        schema = schema
        tablename = 'outcome'

    id = Identifier()
    operation_id = ForeignKey('operation.id', nullable=False, ondelete='CASCADE')
    name = Token(nullable=False)
    description = Text()
    outcome = Enumeration('success failure', nullable=False)
    schema = Definition()

class QueueRegistry(Unit):
    """The queue registry."""

    flux = MeshDependency('flux')
    platoon = MeshDependency('platoon')
    schema = SchemaDependency('flux')

    def register(self, operation):
        self._put_queue(operation)

    def _put_queue(self, operation):
        endpoint = self.flux.prepare('flux/1.0/operation', 'process', operation.id,
            preparation={'type': 'http'})

        Queue(id=operation.queue_id, subject=operation.id, name=operation.name,
            endpoint=endpoint).put()


