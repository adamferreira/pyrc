from genericpath import isdir
import os, platform, sys
from pathlib import Path, PosixPath, WindowsPath
try:
    from subprocess import *
    from subprocess import check_output
    _CMDEXEC_SUBPROCESS_ENABLED_ = True
except:
    _CMDEXEC_SUBPROCESS_ENABLED_ = False

from pyrc.system.filesystem import FileSystem
from pyrc.system.filesystemtree import FileSystemTree
import pyrc.event as pyevent

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
	#		Operators
	# ------------------------
	def __eq__(self, other):
		"""Two LocalFileSystem are considered equals if they are of the same type"""
		return type(self).__name__ == type(other).__name__

	# ------------------------
	#		Overrides
	# ------------------------

	#@overrides (to use non pure paths)
	def abspath(self, path:str) -> str:
		return str(type(self.__path)(path).resolve(strict = True))

	#@overrides
	def realpath(self, path:str) -> str:
		return os.path.realpath(path)

	#@overrides
	def walk0(self, path:str) -> tuple:
		for root, dirs, files in os.walk(path):
			return root, dirs, files

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		event = pyevent.CommandPrettyPrintEvent(self) if event is None else event
		p = Popen(
			cmd,
			cwd = cwd if cwd != "" else None,
			stdin = PIPE, stdout = PIPE, stderr = PIPE,
			# environment = None uses system's env (empty env is assumed as None)
			# TODO: use self.environ ? check other connectors
			env = environment if environment != {} else None,
			shell = True #self.is_unix()
		)
		event.begin(cmd, cwd, p.stdin, p.stdout, p.stderr)
		#p = Popen(f"cd {cwd};{cmd}" if cwd != "" else f"{cmd}", stdin = PIPE, stdout = PIPE, stderr = PIPE, env = environment, shell = self.is_unix())
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
			"release" : platform.release()
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
		if sys.version_info.minor >= 8:
			type(self.__path)(path).unlink(missing_ok)
		else:
			type(self.__path)(path).unlink()

	#@overrides
	def ls(self, path:str)-> 'list[str]':
		root = FileSystemTree.get_root(self, path)
		return root.files + list(root.dirs.keys())
	
	#@overrides
	def lsdir(self, path:str):
		return FileSystemTree.get_tree(self, path)

	#@overrides
	def isfile(self, path:str) -> bool:
		return type(self.__path)(path).is_file()

	#@overrides
	def isexe(self, path:str) -> bool:
		return self.isfile(path) and os.access(path, os.X_OK)

	#@overrides
	def isdir(self, path:str) -> bool:
		return type(self.__path)(path).is_dir()

	#@overrides
	def islink(self, path:str) -> bool:
		return type(self.__path)(path).is_symlink()

	#@overrides
	def touch(self, path:str):
		parent = self.dirname(path)
		if not self.isdir(parent):
			raise RuntimeError(f"Path {parent} is not a valid directory.")
		f = open(path,"w")
		f.close()

	#@overrides
	def zip(self, path:str, archive_path:str = None, flag:str = "") -> str:
		import shutil
		if self.isfile(path):
			return shutil.make_archive(
				# Remove .zip extension when using shutil
				# Where the archive is created
				base_name = path.replace(self.ext(path), ""),
				format = 'zip',
				# root_dir is a directory that will be the root directory of the archive, all paths in the archive will be relative to it; 
				# for example, we typically chdir into root_dir before creating the archive
				root_dir = self.dirname(path),
				# base_dir is the directory where we start archiving from; i.e. base_dir will be the common prefix of all files and directories in the archive.
				# base_dir must be given relative to root_dir.
				base_dir = self.basename(path)
			)
		if self.isdir(path):
			return shutil.make_archive(
				base_name = path,
				format = 'zip',
				root_dir = path
			)

		return None

	#@overrides
	def unzip(self, archive_path:str, to_path:str = None, flag:str = "") -> str:
		import shutil
		folder_path = FileSystem.unzip(self, archive_path, to_path)
		shutil.unpack_archive(filename = archive_path, extract_dir = folder_path)
		# TODO: if extracted is a dir with one file (zipped file)
		# Move the file to .. and remove the dir
		return folder_path

	#@overrides
	def copy(self, src:str, dst:str, follow_symlinks:bool=True):
		import shutil
		return shutil.copy(src, dst, follow_symlinks = follow_symlinks)

	#@overrides
	def getsize(self, path) -> int:
		if self.isfile(path):
			return os.path.getsize(path)
		elif self.isdir(path):
			return FileSystemTree.get_tree(self, path).getsize()
		else:
			return 0

	#@overrides
	def env(self, var:str) -> str:
		return os.environ[var]

# ------------------ LocalFileSystem
