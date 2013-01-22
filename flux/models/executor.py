from spire.schema import *

schema = Schema('flux')

class Executor(Model):
    """A workflow executor."""

    class meta:
        schema = schema
        tablename = 'executor'

    id = Token(nullable=False, primary_key=True)
    description = Text()
    status = Enumeration('active inactive disabled', nullable=False)

class Endpoint(Model):
    """An executor endpoint."""

    class meta:
        polymorphic_on = 'type'
        schema = schema
        tablename = 'endpoint'

    id = Identifier()
    executor_id = ForeignKey('executor.id', nullable=False)

