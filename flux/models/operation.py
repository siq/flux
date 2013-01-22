from spire.mesh import Definition
from spire.schema import *
from sqlalchemy.orm.collections import attribute_mapped_collection

schema = Schema('flux')

class Operation(Model):
    """A workflow operation."""

    class meta:
        schema = schema
        tablename = 'operation'

    id = token(segments=2, nullable=False, primary_key=True)
    name = Text(nullable=False)
    description = Text()
    schema = Definition()

    outcomes = relationship('Outcome', backref='operation',
        collection_class=attribute_mapped_collection('name'),
        cascade='all,delete-orphan', passive_deletes=True)

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
