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

log = LogHelper('flux')
Event = bind(platoon, 'platoon/1.0/event')
ScheduledTask = bind(platoon, 'platoon/1.0/scheduledtask')
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
        
        session = self.schema.session
        subject = self.model.create(session, **data)

        try:
            session.commit()
        except IntegrityError:
            raise OperationError(token='duplicate-workflow-name')

        if 'type' in data and data['type'] == 'mule' and filepath:
            self._schedule_deploy_mulescript(data['name'], filepath)
        return subject

    def delete(self, request, response, subject, data):
        # check if workflow id has been associated with any policy
        policies = subject.policies
        if len(policies):
            log('info', 'workflow_id %s cannot be deleted as it is associated with policies %s', subject.id, policies)
            raise OperationError(token='cannot-delete-inuse-workflow')
        
        # check if workflow id has been executed
        from flux.models import Run
        session = self.schema.session
        runCount = session.query(Run).filter_by(workflow_id=subject.id).count()
        if runCount:
            log('info', 'workflow_id %s cannot be deleted as it has been executed %s times', subject.id, runCount)
            raise OperationError(token='cannot-delete-inuse-workflow')

        # retrieve mule extensions for later use
        mule_extensions = subject.mule_extensions.extract_dict('packageurl endpointurl readmeurl')
        workflowName = subject.name
                                                
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
            self._schedule_undeploy_mulescript(workflowName, package, readme)        

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

        if not 'type' in data:
            data['type'] = subject.type
        if not 'is_service' in data:
            data['is_service'] = subject.is_service
        if subject.type == 'mule':
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

    def _schedule_deploy_mulescript(self, name, filepath):
        ScheduledTask.queue_http_task('deploy-mule-script',
            self.flux.prepare('flux/1.0/workflow', 'task', None,
            {'task': 'deploy-mule-script', 
             'name': name, 'filepath': filepath}))
        
    def _schedule_undeploy_mulescript(self, name, package, readme):            
        ScheduledTask.queue_http_task('undeploy-mule-script',
            self.flux.prepare('flux/1.0/workflow', 'task', None,
            {'task': 'undeploy-mule-script', 
             'name': name, 'package': package, 'readme': readme}))
        
    def _extract_zipfile(self, filepath):
        import zipfile
        from xml.dom import minidom
        endpointurl = ''
        readmeurl = ''
        
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
        return endpointurl, readmeurl
                
    def task(self, request, response, subject, data):
        import urllib2
        import json

        task = data['task']
        if task == 'deploy-mule-script':
            url = MULE_DEPLOY_URL
            scriptName = data['name']
            log('info', 'Deploying Mule script %s by endpoint URL = %s', scriptName, url)
            request = urllib2.Request(url)
            request.add_header('Content-Type', 'application/json')
            conn = None            
            try:
                conn = urllib2.urlopen(request, json.dumps(data))
                log('info', 'Response code of deploying mule script (name: %s) is %s', scriptName, conn.getcode())   
            except urllib2.HTTPError as e:
                log('info', 'Response code of deploying (name: %s) is %s', scriptName, e.code)
                raise OperationError(token='mule-script-deploy-failed')
            finally:
                if conn != None:
                    conn.close()
        elif task == 'undeploy-mule-script':
            url = MULE_UNDEPLOY_URL
            scriptName = data['name']
            log('info', 'UnDeploying Mule script %s by endpoint URL = %s', scriptName, url)
            request = urllib2.Request(url)
            request.add_header('Content-Type', 'application/json')
            conn = None            
            try:
                conn = urllib2.urlopen(request, json.dumps(data))
                log('info', 'Response code of undeploying mule script (name: %s) is %s', scriptName, conn.getcode())   
            except urllib2.HTTPError as e:
                log('info', 'Response code of undeploying (name: %s) is %s', scriptName, e.code)
                raise OperationError(token='mule-script-undeploy-failed')
            finally:
                if conn != None:
                    conn.close()                             