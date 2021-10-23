import os, platform
import shutil
from enum import Enum
from pathlib import Path, PosixPath, WindowsPath
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

class FileSystemTree(object):
	def __init__(self, root:str, parent:FileSystemTree=None, files:'List[str]'=[], dirs:'Dict[str,FileSystemTree]'={}):
		self.root = root
		self.parent = parent
		self.files = files
		self.dirs = dirs
		self.isunix = False

		if parent is None:
			self.level = 0
		else:
			self.level = parent.level + 1

	def __getitem__(self, items):
		return self.dirs[items]

	def __setitem__(self, item, data):
		self.dirs[item] = data

	def __str__(self):
		level = self.level
		indent = ' ' * 4 * (level)
		string = "".join(['{}{}/'.format(indent, self.root), '\n'])
		subindent = ' ' * 4 * (level + 1)
		for f in self.files:
			string = "".join([string, '{}{}'.format(subindent, f), '\n'])

		for d in self.dirs.values():
			string = "".join([string, str(d), '\n'])

		return string

	def __len__(self):
		"""
		Total number of files and folders inside the tree
		"""
		return sum([len(n.files) + len(n.dirs.keys()) for n in self.nodes])

	def nodes(self) -> 'List[FileSystemTree]':
		nodes = [self]
		stack = list(self.dirs.values())
		
		while len(stack) > 0:
			n = stack.pop()
			nodes.append(n)
			
			stack.extend(n.dirs.values())

		return sorted(nodes, key=lambda x: int(x.level))

	def realfiles(self):
		return [os.path.join(self.realpath(), f) for f in self.files]

	def realpath(self):
		return self.root

	def relpath(self)->str:
		ancestors = self.ancestors()
		ancestors.reverse()
		ancestors.append(self)
		return os.path.join(*[n.basename() for n in ancestors])

	def basename(self):
		return os.path.basename(self.realpath())

	def ancestors(self) -> 'List[FileSystemTree]':
		ancestors = []
		p = self.parent
		while p is not None:
			ancestors.append(p)
			p = p.parent

		return ancestors

	def rootnode(self) -> FileSystemTree:
		ancestors = self.ancestors()
		if len(ancestors) == 0:
			return self
		else:
			return ancestors[-1]


	@staticmethod
	def get_tree(directory:str, parent = None):
		tree_root = FileSystemTree(root = os.path.realpath(directory), parent=parent, files=[], dirs={})
		for root, dirs, files in os.walk(tree_root.realpath()):
			tree_root.files = files.copy()
			for dir in dirs :
				tree_root.dirs[dir] = FileSystemTree.get_tree(os.path.join(root, dir), tree_root) 
				#FileSystemTree(root = os.path.join(root, dir), parent=None, files=[], dirs={})
			
			return tree_root

	@staticmethod
	def get_root(directory:str):
		tree_root = FileSystemTree(root = os.path.realpath(directory), parent=None, files=[], dirs={})
		for root, dirs, files in os.walk(tree_root.realpath()):
			tree_root.files = files.copy()
			for dir in dirs :
				tree_root.dirs[dir] = dir

			return tree_root


class FileSystem(object):

	@property
	def ostype(self) -> OSTYPE:
		return self.__ostype

	@property 
	def connector(self) -> SSHConnector:
		return self.__remote

	def is_unix(self) -> bool:
		return self.ostype == OSTYPE.LINUX or self.ostype == OSTYPE.MACOS

	def is_remote(self) -> bool:
		return self.__remote is not None

	@ostype.setter
	def ostype(self, type:OSTYPE):
		self.__ostype = type
		if not self.is_unix():
			self.__path = WindowsPath()
		else:
			self.__path = PosixPath()

	def set_connector(self, remote:SSHConnector):
		if self.is_remote() and not remote.is_open():
			raise RuntimeError("Remote connector must be open")
		self.__remote = remote


	def __init__(self, remote:SSHConnector = None):
		self.__remote:SSHConnector = None
		self.__path:Path = None
		self.__ostype:OSTYPE = None

		self.set_connector(remote)

		# OS deduction from platform.system() info
		if self.is_remote():
			system = self.__remote.platform()["system"]
		else:
			system = platform.system()
			
		
		# Load remote system informations 
		# And should Pathlib path object accordingly 
		if system == "Windows":
			self.ostype = OSTYPE.WINDOWS
		elif "Linux" in system:
			self.ostype = OSTYPE.LINUX
		elif system == "Darwin":
			self.ostype = OSTYPE.MACOS
		else:
			self.ostype = OSTYPE.UNKNOW

	def join(self, *other):
		return str(self.__path.joinpath(*other))
			
	def mkdir(self, path:str, mode=0o777, parents=False, exist_ok=False):
		"""[summary]
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
		if self.is_remote():
			event = pyevent.CommandStoreEvent()
			out, err = [], []
			if self.is_unix():
				flag = " -p " if parents or exist_ok else ""
				"""TODO make mode work on remote machine"""
				#flag = " ".join([flag, "-m " + str(mode)])
				out, err = self.__remote.exec_command(cmd = f"mkdir {flag} {path}", event = event)
			else: # No need for -p flag in Windows
				out, err = self.__remote.exec_command(cmd = f"mkdir {path}", event = event)

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
				out, err = self.exec_command(
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
		"""[summary]
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
				out, err = self.exec_command(
					cmd = f"rm -f {path}",
					event = pyevent.ErrorRaiseEvent()
				)
			else:
				raise RuntimeError("unlink is only available on unix remote systems.")
		else:
			type(self.__path)(path).unlink(missing_ok)
			

	def ls(self, path:str)-> 'List[str]':
		"""[summary]
		Return files and directories in path (no recursion) as a string list
		Returns:
			[type]: [description]
		"""
		if self.is_remote():
			if self.is_unix():
				return self.__remote.check_output(f"ls {path}")
			else:
				return self.__remote.check_output(f"dir {path}")
		else:
			root = FileSystemTree.get_root(path)
			return root.files + list(root.dirs.keys())

	def lsdir(slef, path:str)-> 'FileSystemTree':
		"""[summary]
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

	def isfile(self, path:str)->bool:
		"""[summary]

		Args:
			path (str): [description]

		Raises:
			RuntimeError: [description]

		Returns:
			Return True if the path points to a regular file (or a symbolic link pointing to a regular file), False if it points to another kind of file.
			False is also returned if the path doesn’t exist or is a broken symlink; other errors (such as permission errors) are propagated.
		"""
		if self.is_remote():
			if self.is_unix():
				return "ok" in self.__remote.check_output(f"[[ -f {path} ]] && echo \"ok\"")
			else:
				# TODO
				raise RuntimeError("isfile not supported for Windows remote systems")
			#return self.file_exists_in_folder(self.dirname(path), self.basename(path))
		else:
			return type(self.__path)(path).is_file()

	def isdir(self, path:str)->bool:
		"""[summary]

		Args:
			path (str): [description]

		Raises:
			RuntimeError: [description]

		Returns:
			bool: [description]
		"""
		if self.is_remote():
			if self.is_unix():
				return "ok" in self.__remote.check_output(f"[[ -s {path} ]] && echo \"ok\"")
			else:
				# TODO
				raise RuntimeError("isdir not supported for Windows remote systems")
		else:
			return type(self.__path)(path).is_dir()

	def islink(self, path:str)->bool:
		if self.is_remote():
			if self.is_unix():
				return "ok" in self.__remote.check_output(f"[[ -L {path} ]] && echo \"ok\"")
			else:
				# TODO
				raise RuntimeError("islink not supported for Windows remote systems")
		else:
			return type(self.__path)(path).is_symlink()

	def touch(self, path:str):
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

	def exec_command(self, cmd:str, flags:'list[str]' = [], cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		full_cmd = flags.copy() if flags is not [] else []
		full_cmd.insert(0, cmd)
		full_cmd = " ".join(full_cmd)
		if self.is_remote():
			if _CMDEXEC_REMOTE_ENABLED_ or True:
				return self.__remote.exec_command(full_cmd, cwd, environment, event)
			else:
				raise RuntimeError("Could not load remote connection.")
		else:
			if _CMDEXEC_SUBPROCESS_ENABLED_:
				event = pyevent.CommandPrettyPrintEvent(self, self.path) if event is None else event
				p = Popen([f"cd {cwd};{full_cmd}"], stdin = PIPE, stdout = PIPE, stderr = PIPE, env = environment, shell = True)
				event.begin(cmd, cwd, p.stdin, p.stdout, p.stderr)
				#os.system(full_cmd) #TODO use os.system for realtime python stdout feed ?
				return event.end()
			else:
				raise RuntimeError("Could not load subprocess module.")


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
		out, err = self.__remotefs.exec_command(
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
		"""[summary]
		Execute the given command.
		Use the cached virtual env is it exists.
		Args:
			cmd (str): [Command to execute]
		"""
		event = pyevent.CommandPrettyPrintEvent(self, self.path) if event is None else event
		venv = self.__load_venv_cmd()
		return self.__remotefs.exec_command(
			cmd = f"{venv} {self.python} -c \'{pycmd}\'",
			environment = environment,
			event = event
		)

	def exec_script(self, pyscript:str, environment:dict = None, event:pyevent.Event = None):
		event = pyevent.CommandPrettyPrintEvent(self, self.path) if event is None else event
		venv = self.__load_venv_cmd()

		if not self.__remotefs.isfile(pyscript):
			raise FileNotFoundError(f"{pyscript} cannot be found on remote system.")

		return self.__remotefs.exec_command(
			cmd = f"{venv} {self.python} {pyscript}",
			environment = environment,
			event = event
		)

	def version(self)->str:
		"""[summary]
		Get the remote python installation version
		Returns:
			str: [Python string version]
		"""
		out, err = self.exec_command(
			pycmd = "import sys; print(sys.version_info[0]); print(sys.version_info[1]); print(sys.version_info[2])", 
			event = pyevent.ErrorRaiseEvent())

		return int(out[0]), int(out[1]), int(out[2])


def _create_directory(dir_path):
    os.mkdir(dir_path)

def remove_directory(dir_path):
	for the_file in os.listdir(dir_path):
		file_path = os.path.join(dir_path, the_file)
		try:
			if os.path.isfile(file_path):
				os.unlink(file_path)
			if os.path.isdir(file_path):
				remove_directory(file_path)
		except Exception as e:
			raise(e)

	os.rmdir(dir_path)

def remove_file(file_path):
	os.unlink(file_path)


def cpfile(src_file, dest):
	dest_file = None

	if not os.path.isfile(src_file):
		raise RuntimeError("Cannot copy, source is not a file.")

	if os.path.isfile(dest):
		dest_file = dest
		
	if os.path.isdir(dest):
		src_file_name = os.path.split(src_file)[1]
		dest_file = os.path.join(dest, src_file_name)
	
	shutil.copyfile(src_file, dest_file)

def create_directory(dir_path, override = False):
    # Check if directory already exists :
	if os.path.isfile(dir_path):
		raise RuntimeError("Given file is a file and not a directory.")

	if os.path.isdir(dir_path):
		if override:
			remove_directory(dir_path)
		else:
			raise RuntimeError("Directory " + dir_path + " already exists.")
	
	_create_directory(dir_path)

def list_all_recursivly(folder, ext = None, files_to_exclude = []):
	files = {}
	check_for_ext = False
	ext = [] if ext is None else ext
	ext = [ext] if len(ext) == 1 else ext

	for root, directories, filenames in os.walk(folder):
		if root not in files_to_exclude:
			for filename in filenames:
				if len(ext) > 0:
					for e in ext:
						if filename.endswith(e):
							if root not in files:
								files[root] = []
							if filename not in files_to_exclude:
								files[root].append(filename)
				else:
					if root not in files:
						files[root] = []
					if filename not in files_to_exclude:
						files[root].append(filename)

	return files

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))

def get_size(start_path = '.'):
	total_size = 0
	for dirpath, dirnames, filenames in os.walk(start_path):
		for f in filenames:
			fp = os.path.join(dirpath, f)
			# skip if it is symbolic link
			if not os.path.islink(fp):
				total_size += os.path.getsize(fp)
				
	return total_size