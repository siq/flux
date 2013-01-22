from spire.schema import *

__all__ = ('Run',)

schema = Schema('flux')

class Run(Model):
    """A workflow run."""

    class meta:
        schema = schema
        tablename = 'run'

    id = Identifier()
    workflow_id = ForeignKey('workflow_version.id', nullable=False)
    name = Text(nullable=False)
    status = Enumeration('active completed aborted', nullable=False, default='active')
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)

    threads = relationship('Thread', backref='run', order_by='thread_id')
    steps = relationship('Step', backref='run', order_by='step_id')

    @classmethod
    def create(cls, session, **attrs):
        run = cls(**attrs)
        session.add(run)
        return run
