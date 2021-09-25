from .testutils import *


def test_filesystem_obj_creation(filesystem):
    path, is_local = filesystem.path, filesystem.is_local
    assert path is not None
    

@pytest.mark.depends(on=["test_filesystem_obj_creation"])
def test_filesystem_status(filesystem):
    path, is_local = filesystem.path, filesystem.is_local
    assert is_local is not path.is_remote
    if not is_local:
        assert path.connector.is_open()
    else:
        assert path.connector is None

@pytest.mark.depends(on=["test_filesystem_status"])
def test_current_location(filesystem):
    path, workspace = filesystem.path, filesystem.workspace
    assert path.isdir(workspace)
    assert not path.islink(workspace)

@pytest.mark.depends(on=["test_current_location"])
def test_file_creation(filesystem):
    path, workspace = filesystem.path, filesystem.workspace
    newfile = path.join(workspace, "newfile.txt")
    assert not path.isfile(newfile)
    
