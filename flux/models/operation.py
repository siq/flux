from mesh.standard import bind
from spire.mesh import Definition, MeshDependency
from spire.schema import *
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.bindings import platoon
from flux.constants import *

schema = Schema('flux')

Process = bind(platoon, 'platoon/1.0/process')

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
    parameters = Json()

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

    def initiate(self, tag, input=None, id=None, timeout=None):
        params = {'queue_id': self.queue_id, 'tag': tag}
        if id is not None:
            params['id'] = id
        if input is not None:
            params['input'] = input
        if timeout is not None:
            params['timeout'] = timeout
        return Process.create(**params)

    def update(self, session, outcomes=None, **attrs):
        self.update_with_mapping(**attrs)
        if outcomes is not None:
            collection = self.outcomes
            for name, outcome in outcomes.iteritems():
                if name in collection:
                    collection[name].update_with_mapping(outcome)
                else:
                    collection[name] = Outcome(name=name, **outcome)
            for name in collection.keys():
                if name not in outcomes:
                    del collection[name]

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
