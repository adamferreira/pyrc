
import pytest, os
import pyrc.remote as pyrm
import pyrc.system as pysys
import pyrc.event.event as pyevent

THIS_FILE = os.path.realpath(__file__)
THIS_DIR = os.path.dirname(THIS_FILE)


def create_sparse_file(path:str, bytes:int) -> None:
    f = open(path,"wb")
    f.seek(bytes-1)
    f.write(b"\0")
    f.close()


class FileSystemTest(object):
    def __init__(self, path:pysys.FileSystem, workspace:str, is_local:bool):
        self.path = path
        self.workspace = workspace
        self.is_local = is_local

FILESYSTEM_OBJECTS = [
    FileSystemTest(pysys.FileSystem(), THIS_DIR, True)
]

# All test will be called for each connectors !
@pytest.fixture(params=FILESYSTEM_OBJECTS)
def filesystem(request):
    # Current element of FILESYSTEM_OBJECTS array
    # It should be a pyrc FileSystem obejct !
    return request.param 