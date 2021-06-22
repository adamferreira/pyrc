import os, platform
import shutil
from enum import Enum
from pathlib import Path, PosixPath, WindowsPath

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

class FileSystem(object):
	@property
	def ostype(self) -> OSTYPE:
		return self.__ostype

	def is_unix(self) -> bool:
		return self.ostype == OSTYPE.LINUX or self.ostype == OSTYPE.MACOS

	@ostype.setter
	def ostype(self, type:OSTYPE):
		self.__ostype = type
		if not self.is_unix():
			self.__path = WindowsPath()
		else:
			self.__path = PosixPath()

	def set_remote(self, remote:SSHConnector):
		if remote is not None and not remote.is_open():
			raise RuntimeError("Remote connector must be open")
		self.__remote = remote

	def __init__(self, remote:SSHConnector = None):
		self.__remote:SSHConnector = None
		self.__path:Path = None
		self.__ostype:OSTYPE = None

		self.set_remote(remote)

		if remote is not None:
			system = self.__remote.platform()["system"]
		else:
			system = platform.system()
		
		# Load remote system informations 
		if system == "Windows":
			self.ostype = OSTYPE.WINDOWS
		elif system == "Linux":
			self.ostype = OSTYPE.LINUX
		elif system == "Darwin":
			self.ostype = OSTYPE.MACOS
		else:
			self.ostype = OSTYPE.UNKNOW
			



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

def get_tree(directory):
	return FileSystemTree.get_tree(directory)

def get_size(start_path = '.'):
	total_size = 0
	for dirpath, dirnames, filenames in os.walk(start_path):
		for f in filenames:
			fp = os.path.join(dirpath, f)
			# skip if it is symbolic link
			if not os.path.islink(fp):
				total_size += os.path.getsize(fp)
				
	return total_size