from .testutils import *


def test_filesystem_obj_creation(filesystem):
    path, is_local = filesystem.path, filesystem.is_local
    assert path is not None
    

@pytest.mark.depends(on=["test_filesystem_obj_creation"])
def test_filesystem_status(filesystem):
    path, is_local = filesystem.path, filesystem.is_local
    assert is_local is not path.is_remote()
    if not is_local:
        assert path.connector.is_open()
    else:
        assert path.connector is None

@pytest.mark.depends(on=["test_filesystem_status"])
def test_local_path_joining(filesystem):
    path, is_local = filesystem.path, filesystem.is_local
    if not path.is_remote():
        assert os.path.join("a", "b", "c") == path.join("a", "b", "c")

@pytest.mark.depends(on=["test_filesystem_status", "test_local_path_joining"])
def test_current_location(filesystem):
    path, workspace = filesystem.path, filesystem.workspace
    assert path.isdir(workspace)
    assert not path.islink(workspace)

@pytest.mark.depends(on=["test_current_location"])
def test_file_creation(filesystem):
    """[summary]
    Create (only on local machine) a non-zero file 
    Tests it creation and size, then delete it
    Also test deletion
    Args:
        filesystem ([type]): [description]
    """
    path, workspace = filesystem.path, filesystem.workspace
    newfile = path.join(workspace, "newfile.txt")
    newfile_size = 10 * 8 * (10**6)
    assert not path.isfile(newfile)

    if not path.is_remote():
        # Local file creation
        create_sparse_file(newfile, newfile_size)
        assert path.isfile(newfile)
        assert os.stat(newfile).st_size == newfile_size
        # Detroy local file
        os.unlink(newfile)
        assert not path.isfile(newfile)



    
