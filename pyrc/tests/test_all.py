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

@pytest.mark.depends(on=["test_local_path_joining"])
def test_path_info(filesystem):
    path, workspace = filesystem.path, filesystem.workspace
    assert path.basename(path.join(workspace, "newfile.txt")) == "newfile.txt"
    assert path.dirname(path.join(workspace, "newfile.txt")) == workspace


@pytest.mark.depends(on=["test_current_location"])
def test_ls(filesystem):
    path, workspace = filesystem.path, filesystem.workspace

    files_and_folders = path.ls(workspace)
    assert len(files_and_folders) != 0

    for file_or_folder in files_and_folders:
        assert path.isfile(path.join(workspace, file_or_folder)) or path.isdir(path.join(workspace, file_or_folder))

@pytest.mark.depends(on=["test_ls"])
def test_ls_cmd_unix(filesystem):
    path, workspace = filesystem.path, filesystem.workspace

    # Current test does not work on windows
    if not path.is_unix():
        return 

    files_and_folders_1 = path.ls(workspace)
    files_and_folders_2 = path.exec_command(f"ls {workspace}", event = get_store_event())[0]
    files_and_folders_3 = path.exec_command("ls", cwd = workspace, event = get_store_event())[0]

    assert sorted(files_and_folders_1) == sorted(files_and_folders_2)
    assert sorted(files_and_folders_2) == sorted(files_and_folders_3)
    

@pytest.mark.depends(on=["test_ls"])
def test_mkdir(filesystem):
    """
    Simple test of creatir and deleting empty directory inside the workspace
    Args:
        filesystem ([type]): [description]
    """
    path, workspace = filesystem.path, filesystem.workspace
    # Basic mkdir and rmdir testing
    dirpath = path.join(workspace, "dummy_dir")
    assert not path.isdir(dirpath)
    path.mkdir(dirpath)
    assert path.isdir(dirpath)
    path.rmdir(dirpath)
    assert not path.isdir(dirpath)

    # Testing recreating existing directory
    path.mkdir(dirpath, exist_ok = False)
    assert path.isdir(dirpath)
    try:
        path.mkdir(dirpath, exist_ok = False)
    except Exception as e:
        print(e)
        assert type(e) == RuntimeError or type(e) == FileExistsError
    
    path.mkdir(dirpath, exist_ok = True)
    assert path.isdir(dirpath)
    path.rmdir(dirpath)
    assert not path.isdir(dirpath)



@pytest.mark.depends(on=["test_mkdir"])
def test_mkpath(filesystem):
    """
    Testing the abitlity to create (and delete) the tree:
        a
            b
                c
    In only one mkdir and rmdir command
    Args:
        filesystem ([type]): [description]
    """
    path, workspace = filesystem.path, filesystem.workspace
    assert path.isdir(workspace)
    assert not path.isdir(path.join(workspace, "a"))
    assert not path.isdir(path.join(workspace, "a", "b"))
    assert not path.isdir(path.join(workspace, "a", "b", "c"))
    path.mkdir(path.join(workspace, "a", "b", "c"), parents = True)
    assert path.isdir(path.join(workspace, "a"))
    assert path.isdir(path.join(workspace, "a", "b"))
    assert path.isdir(path.join(workspace, "a", "b", "c"))
    path.rmdir(path.join(workspace, "a"), recur = True)
    assert not path.isdir(path.join(workspace, "a"))
    assert not path.isdir(path.join(workspace, "a", "b"))
    assert not path.isdir(path.join(workspace, "a", "b", "c"))
    assert path.isdir(workspace)
    


@pytest.mark.depends(on=["test_mkpath"])
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

    if not path.is_remote():
        assert not path.isfile(newfile)
        # Local file creation
        create_sparse_file(newfile, newfile_size)
        assert path.isfile(newfile)
        assert os.stat(newfile).st_size == newfile_size
        # Destroy local file
        path.unlink(newfile, missing_ok=False)
        assert not path.isfile(newfile)

@pytest.mark.depends(on=["test_file_creation", "test_path_info"])
def test_touch(filesystem):
    path, workspace = filesystem.path, filesystem.workspace
    newfile = path.join(workspace, "newfile.txt")

    # Create file, test it, and delete it
    # Deletion is already tested by 'test_file_creation'
    assert not path.isfile(newfile)
    path.touch(newfile)
    assert path.isfile(newfile)
    path.unlink(newfile)
    assert not path.isfile(newfile)


@pytest.mark.depends(on=["test_touch"])
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
    remote_path.connector.upload(local_realpath = local_filepath, remote_path = remote_filepath)
    assert remote_path.isfile(remote_filepath)

    # Delete remote file
    remote_path.unlink(remote_filepath, missing_ok=False)
    assert not remote_path.isfile(remote_filepath)

    # Delete local file
    local_path.unlink(local_filepath, missing_ok=False)
    assert not local_path.isfile(local_filepath)

    
