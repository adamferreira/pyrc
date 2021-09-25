import os
from .testutils import *

THIS_FILE = os.path.realpath(__file__)
THIS_DIR = os.path.dirname(THIS_FILE)

def test_filesystem_obj_creation(path):
    assert path is not None

@pytest.mark.depends(on=["test_filesystem_obj_creation"])
def test_current_location(path):
    assert path.isfile(THIS_FILE)
    assert path.isdir(THIS_DIR)
    assert not path.islink(THIS_FILE)
    
