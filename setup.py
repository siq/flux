from distutils.core import setup
from bake.packaging import *

setup(
    name='flux',
    version='0.0.1',
    packages=enumerate_packages('flux'),
    package_data={
        'docket': ['migrations/env.py', 'migrations/script.py.mako',
            'migrations/versions/*.py'],
        'flux.bindings': ['*.mesh'],
    }
)
