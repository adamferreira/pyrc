import os, platform
from pathlib import Path, PosixPath, WindowsPath, PurePosixPath, PureWindowsPath
from pyrc.system.filesystem import FileSystem
import pyrc.event.event as pyevent

try:
    from subprocess import *
    from subprocess import check_output
    _CMDEXEC_SUBPROCESS_ENABLED_ = True
except:
    _CMDEXEC_SUBPROCESS_ENABLED_ = False

# ------------------ LocalFileSystem
class LocalFileSystem(FileSystem):
	def __init__(self) -> None:
		super().__init__()
		# Path deduction from os type
		if self.is_unix():
			self.__path = PosixPath()
		else:
			self.__path = WindowsPath()

	# ------------------------
	#		Overrides
	# ------------------------

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		event = pyevent.CommandPrettyPrintEvent(self) if event is None else event
		p = Popen([f"cd {cwd};{cmd}"], stdin = PIPE, stdout = PIPE, stderr = PIPE, env = environment, shell = True)
		event.begin(cmd, cwd, p.stdin, p.stdout, p.stderr)
		#os.system(full_cmd) #TODO use os.system for realtime python stdout feed ?
		return event.end()

	#@overrides
	def is_remote(self) -> bool:
		return False

	#@overrides
	def is_open(self) -> bool:
		return True

	#@overrides
	def platform(self) -> 'dict[str:str]':
		return {
			"system" : self.system(),
			"release" : "unknown"
		}

	#@overrides
	def system(self) -> str:
		return platform.system()

	#@overrides
	def mkdir(self, path:str, mode=0o777, parents=False, exist_ok=False):
		newpath = type(self.__path)(path)
		newpath.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

	#@overrides
	def rmdir(self, path:str, recur:bool = False):
		def rm_tree(pth):
			pth = Path(pth)
			for child in pth.glob('*'):
				if child.is_file():
					child.unlink()
				else:
					rm_tree(child)
			pth.rmdir()
				
		newpath = type(self.__path)(path)
		if recur:
			rm_tree(newpath)
		else:
			newpath.rmdir()

	#@overrides
	def unlink(self, path:str, missing_ok:bool=False) -> None:
		type(self.__path)(path).unlink(missing_ok)

	#@overrides
	def ls(self, path:str)-> 'List[str]':
		root = FileSystemTree.get_root(path)
		return root.files + list(root.dirs.keys())
	
	#@overrides
	def lsdir(self, path:str):
		return FileSystemTree.get_tree(path)

	#@overrides
	def isfile(self, path:str) -> bool:
		return type(self.__path)(path).is_file()

# ------------------ LocalFileSystem