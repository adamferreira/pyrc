import os, platform
import shutil
from enum import Enum
from pathlib import Path, PosixPath, WindowsPath, PurePosixPath, PureWindowsPath
import pyrc.event.event as pyevent

try:
    from pyrc.remote import SSHConnector
    _CMDEXEC_REMOTE_ENABLED_ = True
except:
    _CMDEXEC_REMOTE_ENABLED_ = False
try:
    from subprocess import *
    from subprocess import check_output
    _CMDEXEC_SUBPROCESS_ENABLED_ = True
except:
    _CMDEXEC_SUBPROCESS_ENABLED_ = False

class FileSystemTree(object):pass
class FileSystem(object):pass
class SSHConnector(object):pass 

class OSTYPE(Enum):
	LINUX = 1
	MACOS = 2
	WINDOWS = 3
	UNKNOW = 4

class FileSystem(object):

	@property
	def ostype(self) -> OSTYPE:
		return self.__ostype

	@property 
	def connector(self) -> SSHConnector:
		return self.__remote

	def is_unix(self) -> bool:
		return self.__ostype == OSTYPE.LINUX or self.__ostype == OSTYPE.MACOS

	def is_remote(self) -> bool:
		return self.__remote is not None

	@ostype.setter
	def ostype(self, type:OSTYPE):
		self.__ostype = type

	def set_connector(self, remote:SSHConnector):
		#if self.is_remote() and not remote.is_open():
		#	raise RuntimeError("Remote connector must be open")
		self.__remote = remote
		
	def system(self) -> str:
		# OS deduction from platform.system() info
		if self.is_remote():
			return self.__remote.platform()["system"]
		else:
			return platform.system()
		
	def __deduce_ostype(self) -> OSTYPE:
		# Load remote system informations 
		# And should Pathlib path object accordingly 
		system = self.system()
		if system == "Windows":
			return OSTYPE.WINDOWS
		elif "Linux" in system:
			return OSTYPE.LINUX
		elif system == "Darwin":
			return OSTYPE.MACOS
		else:
			return OSTYPE.UNKNOW	

	def __init__(self, remote:SSHConnector = None):
		self.__remote:SSHConnector = None
		self.__path:Path = None
		self.__ostype:OSTYPE = None

		self.set_connector(remote)
		self.ostype = self.__deduce_ostype()

		if self.is_remote():
			if self.is_unix():
				self.__path = PurePosixPath()
			else:
				self.__path = PureWindowsPath()
		else:
			if self.is_unix():
				self.__path = PosixPath()
			else:
				self.__path = WindowsPath()

	def join(self, *other):
		if self.is_unix():
			return str(PurePosixPath().joinpath(*other))
		else:
			return str(PureWindowsPath().joinpath(*other))
			
	def mkdir(self, path:str, mode=0o777, parents=False, exist_ok=False):
		"""
		Create a new directory at this given path. If mode is given, it is combined with the process??? umask value to determine the file mode and access flags. 
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
		if self.is_remote():
			event = pyevent.CommandStoreEvent()
			out, err = [], []
			if self.is_unix():
				flag = " -p " if parents or exist_ok else ""
				"""TODO make mode work on remote machine"""
				#flag = " ".join([flag, "-m " + str(mode)])
				out, err, status = self.exec_command(cmd = f"mkdir {flag} {path}", event = event)
			else: # No need for -p flag in Windows
				out, err, status = self.exec_command(cmd = f"mkdir {path}", event = event)

			if len(err) > 0:
				if "File exists" in "".join(err):
					raise FileExistsError('\n'.join(err))
				else:
					raise RuntimeError('\n'.join(err))
		else:
			newpath = type(self.__path)(path)
			newpath.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

	def rmdir(self, path:str, recur:bool = False):
		# TODO doc
		# Keep rmdir and rm_tree in a single method ?
		if self.is_remote():
			if self.is_unix():
				cmd_ = "rm -rf" if recur else "rmdir"
				out, err, status = self.exec_command(
					cmd = f"{cmd_} {path}",
					event = pyevent.ErrorRaiseEvent()
				)
			else:
				raise RuntimeError("rmdir is only available on unix remote systems.")
		else:
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

	def unlink(self, path:str, missing_ok:bool=False):
		"""
		Similar to os.unlink().
		Remove this file or symbolic link. If the path points to a directory, use rmdir() instead.
		If missing_ok is false (the default), FileNotFoundError is raised if the path does not exist.
		If missing_ok is true, FileNotFoundError exceptions will be ignored (same behavior as the POSIX rm -f command).
		Args:
			path (str): [description]
			missing_ok (bool, optional): [description]. Defaults to False.
		"""
		if self.is_remote():
			if not missing_ok and not (self.isfile(path) or self.islink(path)):
				raise FileNotFoundError(f"Remote file {path} does not exist.")

			if self.is_unix():
				out, err, status = self.exec_command(
					cmd = f"rm -f {path}",
					event = pyevent.ErrorRaiseEvent()
				)
			else:
				raise RuntimeError("unlink is only available on unix remote systems.")
		else:
			type(self.__path)(path).unlink(missing_ok)
			

	def ls(self, path:str)-> 'List[str]':
		"""
		Return files and directories in path (no recursion) as a string list
		Returns:
			List[str]: list of files and folders at the root of path
		"""
		if self.is_remote():
			if self.is_unix():
				out, err, status = self.exec_command(cmd = f"ls {path}", event=pyevent.ErrorRaiseEvent())
				return out
			else:
				out, err, status = self.exec_command(cmd = f"dir {path}", event=pyevent.ErrorRaiseEvent())
				return out
		else:
			root = FileSystemTree.get_root(path)
			return root.files + list(root.dirs.keys())

	def lsdir(self, path:str)-> 'FileSystemTree':
		"""
			Return files and directories in path (recursilvy) as a FileSystemTree
		Returns:
			[type]: [description]
		"""
		if self.is_remote():
			# TODO
			raise RuntimeError("lsdir not yet supported for remote paths.")
		else:
			return FileSystemTree.get_tree(path)
		
	def file_exists_in_folder(self, folderpath:str, filename:str)->bool:
		files = self.ls(folderpath)
		return filename in files

	def dirname(self, path:str)->str:
		return str(type(self.__path)(path).parent)

	def basename(self, path:str)->str:
		return str(type(self.__path)(path).name)

	def ext(self, path:str)->str:
		return str(type(self.__path)(path).suffix)

	def isfile(self, path:str)->bool:
		"""

		Args:
			path (str): [description]

		Raises:
			RuntimeError: [description]

		Returns:
			Return True if the path points to a regular file (or a symbolic link pointing to a regular file), False if it points to another kind of file.
			False is also returned if the path doesn???t exist or is a broken symlink; other errors (such as permission errors) are propagated.
		"""
		if self.is_remote():
			if self.is_unix():
				out, err, status = self.exec_command(cmd = f"[[ -f {path} ]] && echo \"ok\"", event=pyevent.ErrorRaiseEvent())
				if len(out) == 0: return False
				else : return "ok" in out[0]
			else:
				# TODO
				raise RuntimeError("isfile not supported for Windows remote systems")
			#return self.file_exists_in_folder(self.dirname(path), self.basename(path))
		else:
			return type(self.__path)(path).is_file()

	def isdir(self, path:str)->bool:
		"""

		Args:
			path (str): [description]

		Raises:
			RuntimeError: [description]

		Returns:
			bool: [description]
		"""
		if self.is_remote():
			if self.is_unix():
				out, err, status = self.exec_command(cmd = f"[[ -s {path} ]] && echo \"ok\"", event=pyevent.ErrorRaiseEvent())
				if len(out) == 0: return False
				else : return "ok" in out[0]
			else:
				# TODO
				raise RuntimeError("isdir not supported for Windows remote systems")
		else:
			return type(self.__path)(path).is_dir()

	def islink(self, path:str)->bool:
		if self.is_remote():
			if self.is_unix():
				out, err, status = self.exec_command(cmd = f"[[ -L {path} ]] && echo \"ok\"", event=pyevent.ErrorRaiseEvent())
				if len(out) == 0: return False
				else : return "ok" in out[0]
			else:
				# TODO
				raise RuntimeError("islink not supported for Windows remote systems")
		else:
			return type(self.__path)(path).is_symlink()

	def touch(self, path:str):
		"""
		Create the file empty <path>
		Args:
			path (str): file to create

		Raises:
			RuntimeError: if parent(path) is not a valid directory
		"""
		parent = self.dirname(path)
		if not self.isdir(parent):
			raise RuntimeError(f"Path {parent} is not a valid directory.")

		if self.is_remote():
			if self.is_unix():
				self.exec_command(f"touch {path}")
			else:
				self.exec_command(f"call > {path}")
		else:
			f = open(path,"w")
			f.close()

	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		if self.is_remote():
			if _CMDEXEC_REMOTE_ENABLED_ or True:
				return self.__remote.exec_command(cmd, cwd, environment, event)
			else:
				raise RuntimeError("Could not load remote connection.")
		else:
			if _CMDEXEC_SUBPROCESS_ENABLED_:
				event = pyevent.CommandPrettyPrintEvent(self) if event is None else event
				p = Popen([f"cd {cwd};{cmd}"], stdin = PIPE, stdout = PIPE, stderr = PIPE, env = environment, shell = True)
				event.begin(cmd, cwd, p.stdin, p.stdout, p.stderr)
				#os.system(full_cmd) #TODO use os.system for realtime python stdout feed ?
				return event.end()
			else:
				raise RuntimeError("Could not load subprocess module.")

	def zip(self, path:str, archivename:str = None, flag:str = ""):
		if (not self.isdir(path)) and (not self.isfile(path)):
			raise RuntimeError(f"Path {path} is not a file or directory.")

		archivename = (path.replace(self.ext(path), ".zip")) if archivename is None else (archivename + ".zip")

		if self.is_remote():
			if self.is_unix():
				return self.exec_command(f"zip {flag} \"{archivename}\" \"{path}\"")
			else:
				return NotImplemented
		else:
			import shutil
			shutil.make_archive(archivename, 'zip', path)


class RemotePython(object):
	def __init__(self, remote:SSHConnector, python_remote_install:str=None, python_virtual_env_path:str=None):
		assert remote is not None
		assert remote.is_open()
		if python_remote_install is not None:
			#assert remote.path.isfile(python_remote_install)
			self.python = python_remote_install
		else:
			self.python = "python3"

		self.__remotefs = remote.path
		self.venv = python_virtual_env_path

	def __load_venv_cmd(self):
		if self.__remotefs.is_unix():
			if self.venv is None:
				return ""
			else:
				return f"source {self.python_virtual_env_path}/bin/activate" + " ; "
		else:
			raise RuntimeError("Cannot load virtual python envs on Windows yet.")

	def create_new_virtual_env(self, python_virtual_env_path:str):
		self.venv = python_virtual_env_path
		out, err, status = self.__remotefs.exec_command(
			cmd = f"{self.python} -m venv {self.venv}", 
			event = pyevent.ErrorRaiseEvent()
		)
		self.python = self.__remotefs.join(python_virtual_env_path, "python")

	def create_virtual_env(self, python_virtual_env_path:str, error_if_exists=True):
		if self.__remotefs.isdir(python_virtual_env_path):
			if error_if_exists:
				raise RuntimeError(f"Python virtual env {python_virtual_env_path} already exists on remote system.")
			else:
				self.venv = python_virtual_env_path
		else:
			self.create_new_virtual_env(python_virtual_env_path)

	def exec_command(self, pycmd:str, environment:dict = None, event:pyevent.Event = None):
		"""
		Execute the given command.
		Use the cached virtual env is it exists.
		Args:
			cmd (str): [Command to execute]
		"""
		event = pyevent.CommandPrettyPrintEvent(self) if event is None else event
		venv = self.__load_venv_cmd()
		return self.__remotefs.exec_command(
			cmd = f"{venv} {self.python} -c \'{pycmd}\'",
			environment = environment,
			event = event
		)

	def exec_script(self, pyscript:str, environment:dict = None, event:pyevent.Event = None):
		event = pyevent.CommandPrettyPrintEvent(self) if event is None else event
		venv = self.__load_venv_cmd()

		if not self.__remotefs.isfile(pyscript):
			raise FileNotFoundError(f"{pyscript} cannot be found on remote system.")

		return self.__remotefs.exec_command(
			cmd = f"{venv} {self.python} {pyscript}",
			environment = environment,
			event = event
		)

	def version(self)->str:
		"""
		Get the remote python installation version
		Returns:
			str: [Python string version]
		"""
		out, err, status = self.exec_command(
			pycmd = "import sys; print(sys.version_info[0]); print(sys.version_info[1]); print(sys.version_info[2])", 
			event = pyevent.ErrorRaiseEvent())

		return int(out[0]), int(out[1]), int(out[2])

