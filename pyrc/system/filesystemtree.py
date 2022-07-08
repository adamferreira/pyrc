from ast import Subscript
from textwrap import indent
from pyrc.system.filesystem import FileSystem

class FileSystemTree(object):pass

class FileSystemTree(object):
	def __init__(self,
			path:FileSystem, 
			root:str,
			parent:FileSystemTree=None, 
			files:'list[str]'=[], 
			dirs:'dict[str,FileSystemTree]'={}
		):
		self.path = path
		self.root = root
		self.parent = parent
		self.files = files
		self.dirs = dirs

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
		#indent, subindent = ' ' * 4 * (level), ' ' * 4 * (level + 1)
		indent, subindent = '\t' * (level), '\t' * (level + 1)
		string = "".join(['{}{}/'.format(indent, self.root),'\n'])
		for f in self.files:
			string = "".join([string, '{}{}'.format(subindent, f), '\n'])

		for d in self.dirs.values():
			# if d is a path not a FileSystemTree (when using getroot for instance)
			if isinstance(d, str):
				string = "".join([string, '{}{}'.format(subindent, d), '\n'])
			# Do not indend if its a tree
			if isinstance(d, FileSystemTree):
				string = "".join([string, str(d), '\n'])

		return string

	def __len__(self):
		"""
		Total number of files and folders inside the tree
		"""
		return sum([len(n.files) + len(n.dirs.keys()) for n in self.nodes])

	def nodes(self) -> 'list[FileSystemTree]':
		nodes = [self]
		stack = list(self.dirs.values())
		
		while len(stack) > 0:
			n = stack.pop()
			nodes.append(n)
			
			stack.extend(n.dirs.values())

		return sorted(nodes, key=lambda x: int(x.level))

	def realfiles(self):
		return [self.path.join(self.realpath(), f) for f in self.files]

	def realpath(self):
		return self.root

	def relpath(self)->str:
		ancestors = self.ancestors()
		ancestors.reverse()
		ancestors.append(self)
		return self.path.join(*[n.basename() for n in ancestors])

	def basename(self):
		return self.path.basename(self.realpath())

	def ancestors(self) -> 'list[FileSystemTree]':
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
	def get_tree(path:FileSystem, directory:str, parent = None):
		tree_root = FileSystemTree(path = path, root = path.realpath(directory), parent=parent, files=[], dirs={})
		root, dirs, files = path.walk0(tree_root.realpath())
		tree_root.files = files.copy()
		for dir in dirs :
			tree_root.dirs[dir] = FileSystemTree.get_tree(path, path.join(root, dir), parent = tree_root) 
		return tree_root

	@staticmethod
	def get_root(path:FileSystem, directory:str):
		tree_root = FileSystemTree(path = path, root = path.realpath(directory), parent=None, files=[], dirs={})
		root, dirs, files = path.walk0(tree_root.realpath())
		tree_root.files = files.copy()
		for dir in dirs :
			tree_root.dirs[dir] = dir
		return tree_root

"""
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
"""