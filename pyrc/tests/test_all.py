from .testutils import *

THIS_FILE = os.path.realpath(__file__)
THIS_DIR = os.path.dirname(THIS_FILE)


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
        # Destroy local file
        path.unlink(newfile, missing_ok=False)
        assert not path.isfile(newfile)


@pytest.mark.depends(on=["test_file_creation"])
def test_file_upload(filesystem):
    """[summary]

    Args:
        filesystem ([type]): [description]
    """
    path, workspace = filesystem.path, filesystem.workspace
    if not path.is_remote():
        return 

    remote_path = path
    local_path = pysys.FileSystem()
    remote_workspace = workspace
    local_workspace = THIS_DIR
    assert remote_path != local_path

    # Create local file before upload
    local_filepath = local_path.join(local_workspace, "newfile.txt")
    assert not path.isfile(local_filepath)
    create_sparse_file(local_filepath, 10 * 8 * (10**6))
    assert local_path.isfile(local_filepath)

    # Define remote (not existing yet) file path
    remote_filepath = remote_path.join(remote_workspace, "newfile.txt")
    # Check that remote workspace is valid and remote file is non-existing
    assert remote_path.isdir(remote_workspace)
    assert not remote_path.isfile(remote_filepath)

    # Upload file to remote workspace
    

    # Destroy local file
    local_path.unlink(local_filepath, missing_ok=False)
    assert not local_path.isfile(local_filepath)




    
