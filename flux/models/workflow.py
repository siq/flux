from spire.schema import *
from sqlalchemy.orm.collections import attribute_mapped_collection

from flux.engine.workflow import Workflow as WorkflowElement

__all__ = ('Workflow', 'WorkflowVersion')

schema = Schema('flux')

class WorkflowCache(object):
    """A cache for parsed workflows."""

    def __init__(self):
        self.cache = {}

    def acquire(self, version):
        try:
            modified, element = self.cache[version.id]
        except KeyError:
            return self._instantiate_version(version)

        if version.modified == modified:
            return element
        else:
            return self._instantiate_version(version)

    def _instantiate_version(self, version):
        element = WorkflowElement.unserialize(version.specification)
        self.cache[version.id] = (version.modified, element)
        return element

class Workflow(Model):
    """A workflow."""

    class meta:
        schema = schema
        tablename = 'workflow'

    id = Identifier()
    name = Text(nullable=False)
    designation = Token(unique=True)

    versions = relationship('WorkflowVersion', backref='workflow',
        collection_class=attribute_mapped_collection('version'),
        cascade='all,delete-orphan', passive_deletes=True)

class WorkflowVersion(Model):
    """A workflow version."""

    class meta:
        constraints = [UniqueConstraint('workflow_id', 'version')]
        schema = schema
        tablename = 'workflow_version'

    id = Identifier()
    workflow_id = ForeignKey('workflow.id', nullable=False, ondelete='CASCADE')
    version = Integer(minimum=1, nullable=False)
    specification = Text(nullable=False)

    cache = WorkflowCache()

    @property
    def name(self):
        return self.workflow.name

    @property
    def workflow(self):
        return self.cache.acquire(self)
