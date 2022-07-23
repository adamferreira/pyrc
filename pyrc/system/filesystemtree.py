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
		# Filesystem to inspect
		self.path = path
		# Abolute path to this node (file or folder)
		self.root = root
		# Parent node
		self.parent = parent
		# Names (basename) of files in this node
		self.files = files
		# Names (basename) of directories in this node
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
		return self.path.basename(self.root)

	def relative_to_root(self) -> str:
		"""
		get relative path of this tree from its root
		"""
		root = self.rootnode()
		return self.path.relative_to(self.realpath(), root.realpath())

	def ancestors(self) -> 'list[FileSystemTree]':
		ancestors = []
		p = self.parent
		while p is not None:
			ancestors.append(p)
			p = p.parent

		return ancestors

	def rootnode(self) -> FileSystemTree:
		"""
		Get the upmost node of the given tree
		"""
		ancestors = self.ancestors()
		if len(ancestors) == 0:
			return self
		else:
			return ancestors[-1]

	def getsize(self) -> int:
		"""
		Get size of the tree as the some of the sizes of all its files
		"""
		return sum([sum([self.path.getsize(f) for f in n.files]) for n in self.nodes()])

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