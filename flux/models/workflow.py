from mesh.exceptions import OperationError
from scheme import current_timestamp
from scheme.exceptions import SchemeError
from spire.core import Unit
from spire.schema import *
from spire.mesh import MeshDependency
from flux.bindings import docket
from sqlalchemy.orm.collections import attribute_mapped_collection
from spire.support.logs import LogHelper

from flux.engine.workflow import Workflow as WorkflowElement

__all__ = ('Workflow', 'WorkflowMule')

schema = Schema('flux')
log = LogHelper('flux')

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
    is_service = Boolean(default=False)
    specification = Text(nullable=False)
    modified = DateTime(timezone=True)
    type = Enumeration(enumeration="yaml mule", nullable=False, default='yaml')
    
    mule_extensions = relationship('WorkflowMule', cascade='all,delete-orphan',
        passive_deletes=True, uselist=False, backref='workflow')

    runs = relationship('Run', backref='workflow')

    @property
    def workflow(self):
        return self.cache.acquire(self)
    
    @property
    def policies(self):
        policyList = []
        # return the list of policy name associated with this workflow
        docket_dependency = DocketDependency()
        Document = docket_dependency.docket_entity.bind('docket.entity/1.0/concert/1.0/document')
        for policy in Document.query().filter(type='policy').all():
            if 'workflow' in policy.attachments['parameters']:
                workflow_id = policy.attachments['parameters']['workflow']
                if self.id == workflow_id:
                    policyList.append(policy.name)
        log('info', 'workflow %s is used by policy %s', self.name, policyList)                    
        return policyList

    @classmethod
    def create(cls, session, **attrs):
        if attrs['type'] == 'mule':        
            mule_extensions = attrs.pop('mule_extensions') 
        subject = cls(modified=current_timestamp(), **attrs)
        if attrs['type'] == 'mule':
            if not mule_extensions['packageurl']:
                raise OperationError(token='mule-script-missing-packageurl')
            elif not mule_extensions['endpointurl']:
                raise OperationError(token='mule-script-missing-endpointurl')
            else:
                # check uniqueness of packageurl/endpointurl/readmeurl
                mulescripts = session.query(Workflow).filter_by(type='mule')
                for mulescript in mulescripts:
                    if mulescript.mule_extensions.packageurl == mule_extensions['packageurl']:
                        raise OperationError(token='mule-script-duplicate-packageurl')
                    if mulescript.mule_extensions.endpointurl == mule_extensions['endpointurl']:
                        raise OperationError(token='mule-script-duplicate-endpointurl')
                    if mule_extensions['readmeurl'] and mule_extensions['readmeurl'].strip() and mulescript.mule_extensions.readmeurl == mule_extensions['readmeurl']:
                        raise OperationError(token='mule-script-duplicate-readmeurl')
                subject.mule_extensions = WorkflowMule(**mule_extensions)
        subject.validate_specification()
        session.add(subject)
        return subject

    def update(self, session, **attrs):
        changed = False
        if 'name' in attrs and attrs['name'] != self.name:
            changed = True
        elif 'specification' in attrs and attrs['specification'] != self.specification:
            self.validate_specification()
            changed = True

        self.update_with_mapping(attrs, ignore='id')
        self.modified = current_timestamp()

        return changed

    def validate_specification(self):
        specification = self.specification
        try:
            self._verify_specification(specification)
        except SchemeError as error:
            raise OperationError(structure={'specification': error})
        return specification

    @classmethod
    def _verify_specification(cls, specification):
        if specification is None:
            return

        schema = WorkflowElement.unserialize(specification)
        schema.verify()

class WorkflowMule(Model):
    """Mule extension."""

    class meta:
        schema = schema
        tablename = 'workflow_mule'

    id = Identifier()
    workflow_id = ForeignKey('workflow.id', nullable=False, ondelete='CASCADE')
    packageurl = Text(unique=True, nullable=False)
    endpointurl = Text(unique=True, nullable=False)
    readmeurl = Text()
    
class DocketDependency(Unit):
    docket_entity = MeshDependency('docket.entity')