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
    print(f"The user is {user}")
    print(f"The current directory is {workspace}")
    print(f"Are we on a remote system ? -> {path.is_remote()}")
    print(f"Are we on an open system ? -> {path.is_open()}")
    print(f"Are we on an unix system ? -> {path.is_unix()}")


if __name__ == '__main__':
    test_fs(pysys.LocalFileSystem(), currentdir())
