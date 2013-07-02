from mesh.exceptions import GoneError
from mesh.standard import bind
from scheme import current_timestamp
from spire.schema import *
from spire.support.logs import LogHelper

from flux.bindings import platoon
from flux.constants import *

__all__ = ('WorkflowExecution',)

log = LogHelper('flux')
schema = Schema('flux')

Process = bind(platoon, 'platoon/1.0/process')

class WorkflowExecution(Model):
    """A step execution."""

    class meta:
        constraints = [UniqueConstraint('run_id', 'execution_id')]
        schema = schema
        tablename = 'execution'

    id = Identifier()
    run_id = ForeignKey('run.id', nullable=False, ondelete='CASCADE')
    execution_id = Integer(minimum=1, nullable=False)
    ancestor_id = ForeignKey('execution.id')
    step = Token(nullable=False)
    name = Text()
    status = Enumeration(RUN_STATUSES, nullable=False, default='pending')
    outcome = Token()
    started = DateTime(timezone=True)
    ended = DateTime(timezone=True)
    parameters = Json()

    descendants = relationship('WorkflowExecution',
        backref=backref('ancestor', remote_side=[id]))

    def __repr__(self):
        return 'WorkflowExecution(id=%r, execution_id=%r, status=%r)' % (
                self.id, self.execution_id, self.status)

    @property
    def is_active(self):
        return self.status in ACTIVE_RUN_STATUSES.split(' ')

    @property
    def workflow(self):
        return self.run.workflow

    def abort(self, session):
        self.status = 'aborted'
        self.ended = current_timestamp()
        try:
            Process.execute('update', {'status': 'aborted'}, subject=self.id)
        except GoneError:
            log('warning', 'no corresponding process resource for %r', self)

    def complete(self, session, outcome):
        self.status = 'completed'
        self.outcome = outcome

    def contribute_values(self):
        step = self.extract_dict('id execution_id step name status outcome started ended')
        step['serial'] = self.execution_id
        return {'step': step}

    @classmethod
    def create(cls, session, **attrs):
        execution = cls(**attrs)
        session.add(execution)
        return execution

    def fail(self, session, outcome=None):
        self.status = 'failed'
        if outcome:
            self.outcome = outcome

    def invalidate(self, session, errors):
        self.status = 'invalidated'

    def process(self, session, status, output):
        workflow = self.workflow.workflow
        step = workflow.steps[self.step]

        self.ended = current_timestamp()

        session.begin_nested()
        try:
            step.process(session, self, workflow, status, output)
        except Exception:
            session.rollback()
            log('exception', 'processing of %r failed due to exception', self)
            self.run.fail(session)
        else:
            session.commit()

    def start(self, parameters=None):
        self.started = current_timestamp()
        if parameters:
            self.parameters = parameters

    def timeout(self, session):
        self.status = 'timedout'

    def update_progress(self, session, progress):
        pass
        # TODO: handle progress_update
