from distutils.core import setup
from bake.packaging import *

setup(
    name='flux',
    version='0.0.1',
    packages=enumerate_packages('flux'),
    package_data={
        'flux.bindings': ['*.mesh'],
    }
)
