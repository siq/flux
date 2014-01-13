from .mediation import *
from .request import *
from .test import *

OPERATIONS = {
    CreateRequest.id: CreateRequest,
    MediateSurrogates.id: MediateSurrogates,
    TestOperation.id: TestOperation,
}
