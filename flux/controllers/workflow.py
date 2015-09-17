from mesh.exceptions import OperationError
from mesh.standard import bind
from spire.core import Dependency
from spire.mesh import MeshDependency, ModelController, support_returning
from spire.schema import SchemaDependency, IntegrityError
from spire.support.logs import LogHelper
from spire.wsgi.upload import UploadManager

from flux.bindings import truss, platoon
from flux.constants import *
from flux.models import *
from flux.resources import Workflow as WorkflowResource
from flux.engine.workflow import Workflow as WorkflowEngine

import urllib2
import json

log = LogHelper('flux')
Event = bind(platoon, 'platoon/1.0/event')
ExternalUrl = bind(truss, 'truss/1.0/externalurl')

class WorkflowController(ModelController):
    resource = WorkflowResource
    version = (1, 0)

    model = Workflow
    mapping = 'id name designation is_service specification modified type'
    schema = SchemaDependency('flux')
    uploads = Dependency(UploadManager)
    flux = MeshDependency('flux')
    docket_entity = MeshDependency('docket.entity')

    @support_returning
    def create(self, request, response, subject, data):
        if 'type' in data and data['type'] == 'mule':
            # check the duplication of workflow name before proceed
            session = self.schema.session
            if session.query(Workflow).filter(Workflow.name==data['name']).count():
              raise OperationError(token='duplicate-workflow-name')
            
            data['specification'] = MULE_DUMMY_SPEC # set no-op yaml spec to mule script          
            if not 'mule_extensions' in data: # if mule_extensions doesn't exist, get the extension information from mule archive
                data['mule_extensions'] = {}
                if not data['filepath']:
                    raise OperationError(token='mule-script-upload-required')
                else:
                    shortFilePath = data['filepath'][37:] # assume the uuid_ has fixed length of 37, e.g. 25dc766a-7eb6-4ed6-abc6-2f57fbfbc294_helloworld.zip
                    data['mule_extensions']['packageurl'] = ExternalUrl.create(path='/download/mule-flows/%s' % shortFilePath).url              
                    try:
                        filepath = self.uploads.find(data.pop('filepath'))
                    except ValueError:
                        raise OperationError(token='mule-script-invalid-upload')
                endpointurl, readmeurl = self._extract_zipfile(filepath)
                data['mule_extensions']['endpointurl'] = endpointurl
                data['mule_extensions']['readmeurl'] = readmeurl
                self._deploy_mulescript(data['name'], filepath)
        
        session = self.schema.session
        subject = self.model.create(session, **data)

        try:
            session.commit()
        except IntegrityError:
            raise OperationError(token='duplicate-workflow-name')

        return subject

    def delete(self, request, response, subject, data):
        workflowName = subject.name
        # check if workflow id has been associated with any policy
        policies = subject.policies
        if len(policies):
            log('info', 'workflow %s (%s) cannot be deleted as it is associated with policies %s', subject.id, workflowName, policies)
            raise OperationError(token='cannot-delete-inuse-workflow')
        
        # check if the run has uncompleted instances
        session = self.schema.session
        if session.query(Run).filter(Run.workflow_id==subject.id, Run.status.in_(ACTIVE_RUN_STATUSES.split(' '))).count():
            log('info', 'workflow %s (%s) cannot be deleted as it has run with uncompleted status of either %s', subject.id, workflowName, ACTIVE_RUN_STATUSES)
            raise OperationError(token='cannot-delete-uncompleted-workflow')
        # delete the completed runs
        for run in session.query(Run).filter_by(workflow_id=subject.id).all():
            runEntity = self.docket_entity.bind('docket.entity/1.0/flux/1.0/run')
            runInstance = runEntity.get(run.id)
            runInstance.destroy()

        # retrieve mule extensions for later use
        if subject.type == 'mule':
            mule_extensions = subject.mule_extensions.extract_dict('packageurl endpointurl readmeurl')
                                                
        super(WorkflowController, self).delete(request, response, subject, data)
        self._create_change_event(subject)
        
        if subject.type == 'mule':
            # retrieve mule_extensions info
            packageurl = mule_extensions['packageurl']
            package = packageurl.split('/')[-1] # get mule app name from packageurl
            readmeurl = mule_extensions['readmeurl']
            readme = ''            
            if readmeurl:
                readme = readmeurl.split('/')[-1] # get mule readme name from readmeurl        
            self._undeploy_mulescript(workflowName, package, readme)        

    def generate(self, request, response, subject, data):
        name = data['name']
        description = data.get('description', '')
        operations = data['operations']

        specification = {
            'name': name,
            'entry': 'step:0',
        }
        layout = data.get('layout')
        schema = data.get('schema')
        if layout:
            specification['layout'] = layout
        if schema:
            specification['schema'] = schema

        steps = {}
        step_name = None
        for i, op in enumerate(operations):
            new_step_name = 'step:%s' % i
            new_step = {
                'operation': op['operation'],
                'parameters': op['run_params'],
                'description': op.get('description'),
            }
            if step_name:
                steps[step_name]['postoperation'] = [{
                    'actions': [{
                        'action': 'execute-step',
                        'step': new_step_name,
                        'parameters': op.get('step_params'),
                    }],
                    'terminal': False,
                }]

            step_name = new_step_name
            steps[step_name] = new_step

        specification['steps'] = steps
        specification = WorkflowEngine.schema.serialize(specification,
                format='yaml')

        response({'name': name, 'specification': specification, 'description': description})

    @support_returning
    def update(self, request, response, subject, data):
        if not data:
            return subject

        if subject.type == 'mule':
            if 'type' in data:
                data.pop('type') # no update of workflow type
            if 'is_service' in data:
                data.pop('is_service') # no update of workflow is_service                
            if 'mule_extensions' in data:
                data.pop('mule_extensions') # no update of mule extensions is allowed
        
        session = self.schema.session
        changed = subject.update(session, **data)

        try:
            session.commit()
        except IntegrityError:
            raise OperationError(token='duplicate-workflow-name')

        if changed:
            self._create_change_event(subject)
        return subject

    def _annotate_resource(self, request, model, resource, data):
        if model.type == 'mule':
            resource['mule_extensions'] = model.mule_extensions.extract_dict('packageurl endpointurl readmeurl')
        
        include = data and data.get('include')
        if not include:
            return

        if 'form' in include:
            schema = model.workflow.schema
            layout = model.workflow.layout

            form = {}
            if layout:
                form['layout'] = layout
            if schema:
                form['schema'] = schema

            resource['form'] = form or None

        if 'specification' in include:
            resource['specification'] = model.specification
            
        if 'policies' in include:            
            resource['policies'] = model.policies

    def _create_change_event(self, subject):
        try:
            Event.create(topic='workflow:changed', aspects={'id': subject.id})
        except Exception:
            log('exception', 'failed to fire workflow:changed event')

    def _deploy_mulescript(self, name, filepath):
        url = MULE_DEPLOY_URL
        scriptName = name
        log('info', 'Deploying Mule script %s by endpoint URL = %s', scriptName, url)
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json')
        conn = None            
        try:
            conn = urllib2.urlopen(request, json.dumps({'name': name, 'filepath': filepath}))
            log('info', 'Response code of deploying mule script (name: %s) is %s', scriptName, conn.getcode())   
        except urllib2.HTTPError as e:
            log('info', 'HTTPError Response code of deploying (name: %s) is %s', scriptName, e.code)
            raise OperationError(token='mule-script-deploy-failed')
        finally:
            if conn != None:
                conn.close()
        
    def _undeploy_mulescript(self, name, package, readme):            
        url = MULE_UNDEPLOY_URL
        scriptName = name
        log('info', 'UnDeploying Mule script %s by endpoint URL = %s', scriptName, url)
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json')
        conn = None            
        try:
            conn = urllib2.urlopen(request, json.dumps({'name': name, 'package': package, 'readme': readme}))
            log('info', 'Response code of undeploying mule script (name: %s) is %s', scriptName, conn.getcode())   
        except urllib2.HTTPError as e:
            log('exception', 'HTTPError Response code of undeploying (name: %s) is %s, failed to undeploy mule script', scriptName, e.code)
        finally:
            if conn != None:
                conn.close()
                            
    def _extract_zipfile(self, filepath):
        import zipfile
        from xml.dom import minidom
        endpointurl = ''
        readmeurl = ''
        
        try:
            with zipfile.ZipFile(filepath, 'r') as f:
                # get all files in zip
                comp_files = f.namelist()
                for comp_file in comp_files:               
                    if comp_file.endswith('xml') and not '/' in comp_file:
                        # open xml file and file "path" under http:listener
                        cfp = f.open(comp_file, 'r')
                        xmldoc = minidom.parse(cfp)
                        httplistener = xmldoc.getElementsByTagName('http:listener')
                        if httplistener:
                            urlpath = httplistener[0].getAttribute('path')
                            if urlpath:
                                if urlpath.startswith('/'):
                                    urlpath = urlpath[1:] # remove "/" from urlpath
                                endpointurl = MULE_ENDPOINT_URL_PREFIX + urlpath
                            else:
                                raise OperationError(token='mule-script-missing-http-path')                                
                        else:
                            raise OperationError(token='mule-script-missing-endpoint')
                    if comp_file.endswith(MULE_README_EXT) and not '/' in comp_file:
                        readmeurl = ExternalUrl.create(path='/download/mule-flows/%s' % comp_file).url
        except Exception, e:
            log('info', 'Unable to unzip file %s : %s', filepath, str(e))
            raise OperationError(token='mule-script-bad-zipfile')
        return endpointurl, readmeurl
