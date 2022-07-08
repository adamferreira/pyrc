import pyrc
import pyrc.remote as pyrm
import pyrc.system as pysys
import pyrc.event as pyevent

def currentdir():
    p = pysys.LocalFileSystem()
    return p.abspath(p.dirname(__file__))

def test_fs(
        path:pysys.FileSystem,
        workspace:str
    ):
    user = path.env("USER")
    tmpdir = path.join(workspace, "tmp")
    print(f"The user is -> {user}")
    print(f"The current file is -> {path.basename(__file__)}")
    print(f"The current file extension is -> {path.ext(__file__)}")
    print(f"The current directory is -> {path.dirname(__file__)}")
    print(f"The current full path is -> {path.abspath(workspace)}")
    print(f"Are we on a remote system ? -> {path.is_remote()}")
    print(f"Are we on an open system ? -> {path.is_open()}")
    print(f"Are we on an unix system ? -> {path.is_unix()}")
    print(f"Current platform -> {path.platform()}")
    print(f"Current system -> {path.system()}")

    assert path.isfile(__file__)
    assert path.isdir(workspace)

    print(f"Creating temporary folder {tmpdir} ...")
    path.mkdir(tmpdir)
    assert path.isdir(tmpdir)
    print("Done !")

    tmpfile = path.join(tmpdir, "tmpfile.txt")
    print(f"Creating temporary file {tmpfile} ...")
    path.touch(tmpfile)
    assert path.isfile(tmpfile)
    assert not path.isdir(tmpfile)
    assert not path.islink(tmpfile)
    assert "tmpfile.txt" in path.ls(tmpdir)
    print("Done !")
    print(f"Deleting temporary file {tmpfile} ...")
    path.unlink(tmpfile)
    assert not path.isfile(tmpfile)
    assert not "tmpfile.txt" in path.ls(tmpdir)
    print("Done !")

    print(f"Deleteing temporary folder {tmpdir} ...")
    path.rmdir(tmpdir)
    assert not path.isdir(tmpdir)
    print("Done !")


if __name__ == '__main__':
    #test_fs(pysys.LocalFileSystem(), currentdir())
    print(pysys.FileSystemTree.get_root(pysys.LocalFileSystem(), pysys.LocalFileSystem().dirname(currentdir())))
    print(pysys.FileSystemTree.get_tree(pysys.LocalFileSystem(), pysys.LocalFileSystem().dirname(currentdir())))
