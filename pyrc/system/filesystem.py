from pathlib import Path, PosixPath, WindowsPath, PurePosixPath, PureWindowsPath
from pyrc.system.connector import Connector

# ------------------ FileSystem
class FileSystem(object):
    def __init__(self, connector:Connector = None) -> None:
        self.__connector = connector
        self.__local = None # Local connector

    def copy(source:str, destination:str):
        # Source should be a valid LOCAL path
        # Destination should be a valid path WITHIN the connector
        return NotImplemented

# ------------------ FileSystem