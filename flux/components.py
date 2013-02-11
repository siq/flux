from spire.core import Component, Dependency
from spire.mesh import MeshDependency, MeshServer

import flux.models
from flux.bundles import API
from flux.resources import *

class Flux(Component):
    api = MeshServer.deploy(bundles=[API])
