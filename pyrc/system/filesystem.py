from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath
import pyrc.event.event as pyevent

class OSTYPE(Enum):
	LINUX = 1
	MACOS = 2
	WINDOWS = 3
	UNKNOW = 4

# ------------------ FileSystem
class FileSystem:

	class EnvironDict(dict[str:str]):
		def __init__(self, path:'FileSystem'):
			super().__init__()
			self.__path = path

		def __getitem__(self, key:str) -> str:
			if key in self:
				return super().__getitem__(key)
			else:
				self.__setitem__(key, self.__path.env(key))
				return super().__getitem__(key)

		def __setitem__(self, key, value):
			return super().__setitem__(key, value)

	@property
	def ostype(self) -> OSTYPE:
		return self.__ostype

	@ostype.setter
	def ostype(self, type:OSTYPE):
		self.__ostype = type

	def __deduce_ostype(self) -> OSTYPE:
		system = self.system()
		if system == "Windows":
			return OSTYPE.WINDOWS
		elif "Linux" in system:
			return OSTYPE.LINUX
		elif system == "Darwin":
			return OSTYPE.MACOS
		else:
			return OSTYPE.UNKNOW
			
	@staticmethod
	def os_to_str(os:OSTYPE) -> str:
		if os == OSTYPE.WINDOWS:
			return "Windows"
		elif os  == OSTYPE.LINUX:
			return "Linux"
		elif os == OSTYPE.MACOS:
			return "MacOS"
		else:
			return "unknown"

	def __init__(self) -> None:
		self.__ostype:OSTYPE = self.__deduce_ostype()
		# Path deduction from os type
		if self.is_unix():
			self.__path = PurePosixPath()
		else:
			self.__path = PureWindowsPath()

		# Environment variables
		self.environ = FileSystem.EnvironDict(self)

	# ------------------------
	#		Custom functions
	# ------------------------

	def join(self, *other):
		if self.is_unix():
			return str(PurePosixPath().joinpath(*other))
		else:
			return str(PureWindowsPath().joinpath(*other))

	def file_exists_in_folder(self, folderpath:str, filename:str) -> bool:
		files = self.ls(folderpath)
		return filename in files

	def dirname(self, path:str) -> str:
		return str(type(self.__path)(path).parent)

	def basename(self, path:str) -> str:
		return str(type(self.__path)(path).name)

	def abspath(self, path:str) -> str:
		return str(type(self.__path)(path).resolve(strict = True))

	def ext(self, path:str) -> str:
		return str(type(self.__path)(path).suffix)

	def convert(self, path:str) -> str:
		"""
		Convert given path tu current path type (Posix or Windows)
		"""
		return str(type(self.__path)(path))

	def relative_to(self, path:str, other:str) -> str:
		"""
		Compute a version of this path relative to the path represented by other. 
		If it’s impossible, ValueError is raised
		"""
		return str(type(self.__path)(path).relative_to(other))

	# ------------------------
	#		To Override
	# ------------------------

	def name(self) -> str:
		return str(type(self).__name__)

	def realpath(self, path:str) -> str:
		"""
		Args:
			path (str): path to resolve

		Returns:
			The canonical path of the specified filename by eliminating any symbolic links encountered in the path.
		"""
		return NotImplemented

	def walk0(self, path:str) -> tuple:
		"""
		equivalement to os.walk[0]
		"""
		return NotImplemented

	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		"""
		Executes the given command on the connected system in a given directory
		Args:
			cmd (str): command to execute
			cwd (str, optional): current working directory. Defaults to "".
			environment (dict, optional): environment variables. Defaults to None.
			event (pyevent.Event, optional): event to plug the command to. Defaults to None.

		Returns:
			event outputs
		"""
		return NotImplemented

	def is_remote(self) -> bool:
		"""
		Tells wether or not this connector would execute action on a remote machine
		Returns:
			bool
		"""
		return NotImplemented

	def is_open(self) -> bool:
		"""
		Tells wether or not this connector is up and running
		Returns:
			bool
		"""
		return NotImplemented

	def is_unix(self) -> bool:
		"""
		Tells wether or not this connector would execute action on a unix or windows machine
		Returns:
			bool
		"""
		return self.__ostype == OSTYPE.LINUX or self.__ostype == OSTYPE.MACOS

	def platform(self) -> 'dict[str:str]':
		"""
		Get connected system informations
		Raises:
			RuntimeError
		Returns:
			[dict[str:str]]: A dict of remote system informations. Keys are 'system' and 'release'
		"""
		return NotImplemented

	def system(self) -> str:
		"""
		Get connected system informations
		Raises:
			RuntimeError
		"""
		return self.platform()["system"]

	def mkdir(self, path:str, mode=0o777, parents=False, exist_ok=False):
		"""
		Create a new directory at this given path. If mode is given, it is combined with the process’ umask value to determine the file mode and access flags. 
		If the path already exists, FileExistsError is raised.
		If parents is true, any missing parents of this path are created as needed; 
		they are created with the default permissions without taking mode into account (mimicking the POSIX mkdir -p command).
		If parents is false (the default), a missing parent raises FileNotFoundError.
		If exist_ok is false (the default), FileExistsError is raised if the target directory already exists.
		If exist_ok is true, FileExistsError exceptions will be ignored (same behavior as the POSIX mkdir -p command), 
		but only if the last path component is not an existing non-directory file.
		Args:
			path (str): [description]
			mode ([type], optional): [description]. Defaults to 0o777.
			parents (bool, optional): [description]. Defaults to False.
			exist_ok (bool, optional): [description]. Defaults to False.

		Raises:
			FileExistsError: [description]
			RuntimeError: [description]
			OSError: [description]
		"""
		return NotImplemented

	def rmdir(self, path:str, recur:bool = False):
		# TODO doc
		# Keep rmdir and rm_tree in a single method ?
		return NotImplemented

	def unlink(self, path:str, missing_ok:bool=False) -> None:
		"""
		Similar to os.unlink().
		Remove this file or symbolic link. If the path points to a directory, use rmdir() instead.
		If missing_ok is false (the default), FileNotFoundError is raised if the path does not exist.
		If missing_ok is true, FileNotFoundError exceptions will be ignored (same behavior as the POSIX rm -f command).
		Args:
			path (str): path to remove
			missing_ok (bool, optional): Defaults to False.
		"""
		return NotImplemented

	def ls(self, path:str) -> 'List[str]':
		"""
		Return files and directories in path (no recursion) as a string list
		Returns:
			List[str]: list of files and folders at the root of path
		"""
		return NotImplemented

	def lsdir(self, path:str) -> 'FileSystemTree':
		"""
			Return files and directories in path (recursilvy) as a FileSystemTree
		Returns:
			FileSystemTree: Tree reprensenting the path directory structure
		"""
		return NotImplemented

	def isfile(self, path:str) -> bool:
		"""
		Args:
			path (str): path to check

		Raises:
			RuntimeError:

		Returns:
			Return True if the path points to a regular file (or a symbolic link pointing to a regular file), False if it points to another kind of file.
			False is also returned if the path doesn’t exist or is a broken symlink; other errors (such as permission errors) are propagated.
		"""
		return NotImplemented

	def isdir(self, path:str) -> bool:
		"""
		Args:
			path (str): path to check

		Raises:
			RuntimeError

		Returns:
		True if the path points to a directory (or a symbolic link pointing to a directory), 
		False if it points to another kind of file.
		False is also returned if the path doesn’t exist or is a broken symlink; 
		other errors (such as permission errors) are propagated.
		"""
		return NotImplemented

	def islink(self, path:str) -> bool:
		"""
		Args:
			path (str): path to check

		Returns:
		True if the path points to a symbolic link, False otherwise.
		False is also returned if the path doesn’t exist; other errors 
		(such as permission errors) are propagated.
		"""
		return NotImplemented

	def touch(self, path:str) -> None:
		"""
		Create the file empty <path>
		Args:
			path (str): file to create

		Raises:
			RuntimeError: if parent(path) is not a valid directory
		"""
		return NotImplemented

	def zip(self, path:str, archive_path:str = None, flag:str = "") -> str:
		if (not self.isdir(path)) and (not self.isfile(path)):
			raise RuntimeError(f"Path {path} is not a file or directory.")

		if self.isdir(path):
			return path + ".zip" if archive_path is None else (archive_path + ".zip") 

		if self.isfile(path):
			return (path.replace(self.ext(path), ".zip")) if archive_path is None else (archive_path + ".zip")

	def unzip(self, archive_path:str, to_path:str = None, flag:str = "") -> str:
		if not self.ext(archive_path) == ".zip":
			raise RuntimeError(f"Cannot unzip format {self.ext(archive_path)}")
			
		if to_path is not None and not self.isdir(to_path):
			raise RuntimeError(f"Path {to_path} is not a valid directory")
		
		if to_path is None:
			return archive_path.replace(self.ext(archive_path), "")

		return to_path


	def getsize(self, path) -> int:
		"""
		Args:
			path (str): path to analyse

		Returns:
			int: size (in bytes) of the path (file or folder)
		"""
		return NotImplemented

	def append(self, line:str, file:str) -> None:
		"""
		Append the given file with the given line
		"""
		return NotImplemented

	def env(self, var:str) -> str:
		return NotImplemented
		

# ------------------ FileSystem
