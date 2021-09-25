
import pytest
import pyrc.remote as pyrm
import pyrc.system as pysys
import pyrc.event.event as pyevent


FILESYSTEM_OBJECTS = [
    pysys.FileSystem()
]

# All test will be called for each connectors !
@pytest.fixture(params=FILESYSTEM_OBJECTS)
def path(request):
    # Current element of FILESYSTEM_OBJECTS array
    # It should be a pyrc FileSystem obejct !
    return request.param 