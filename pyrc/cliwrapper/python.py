from pyrc.system import FileSystem
from pyrc.cliwrapper import CLIWrapper

class Python(CLIWrapper):
    def __init__(self, pyexe:str = "python3", connector:FileSystem = None) -> None:
        super().__init__(connector)
        if not self.connector.isexe(pyexe):
            raise RuntimeError(f"Python exe {pyexe} is not a valid path.")