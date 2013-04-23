from scheme import current_timestamp
from spire.schema import *
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.engine.workflow import Workflow as WorkflowElement

schema = Schema('flux')

class WorkflowCache(object):
    def __init__(self):
        self.cache = {}

    def acquire(self, workflow):
        try:
            modified, element = self.cache[workflow.id]
        except KeyError:
            return self.instantiate(workflow)

        if workflow.modified == modified:
            return element
        else:
            return self.instantiate(workflow)

    def instantiate(self, workflow):
        element = WorkflowElement.unserialize(workflow.specification)
        self.cache[workflow.id] = (workflow.modified, element)
        return element

class Workflow(Model):
    """A workflow."""

    class meta:
        schema = schema
        tablename = 'workflow'

    cache = WorkflowCache()

    id = Identifier()
    name = Text(unique=True, nullable=False)
    designation = Token(unique=True)
    specification = Text(nullable=False)
    modified = DateTime(timezone=True)

    runs = relationship('Run', backref='workflow')

    @property
    def workflow(self):
        return self.cache.acquire(self)

    @classmethod
    def create(cls, session, **attrs):
        cls._verify_specification(attrs.get('specification'))
        subject = cls(modified=current_timestamp(), **attrs)
        session.add(subject)
        return subject

    def update(self, session, **attrs):
        self._verify_specification(attrs.get('specification'))
        self.update_with_mapping(attrs, ignore='id')
        self.modified = current_timestamp()

    @classmethod
    def _verify_specification(cls, specification):
        if specification is None:
            return

        schema = WorkflowElement.unserialize(specification)
        schema.verify()
