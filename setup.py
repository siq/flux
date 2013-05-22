from distutils.core import setup
from bake.packaging import *

#test
setup(
    name='flux',
    version='0.0.1',
    packages=enumerate_packages('flux'),
    package_data={
        'flux': ['migrations/env.py', 'migrations/script.py.mako',
            'migrations/versions/*.py'],
        'flux.bindings': ['*.mesh'],
    }
)
