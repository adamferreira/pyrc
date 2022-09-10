import pyrc.event.event as pyevent
from pyrc.system.filesystemtree import FileSystemTree
from pyrc.system.filesystem import OSTYPE, FileSystem

try:
	from scp import SCPClient
	_CMDEXEC_REMOTE_ENABLED_ = True
except BaseException as err:
	_CMDEXEC_REMOTE_ENABLED_ = False

def transfer_files(from_paths:'list[str]', to_path:str, from_fs:FileSystem, to_fs:FileSystem):
	"""
	Transfert FILES from one filesystem to a directory in another one
	Args:
		from_paths (list[str]): List of files to be transfered from 
		'from_fs' filesystem to 'to_fs' filesystem.
		Le list must represent files that exists in filesystel 'from_fs'
		to_path (str): Path to a directory in filesystem 'to_fs'
		from_fs (FileSystem): Filesystem to transfert from
		to_fs (FileSystem): Filesystem to transfert to
	"""

	# Format path according to their filesystems
	from_paths = [from_fs.abspath(from_path) for from_path in from_paths]
	to_path = to_fs.abspath(to_path)

	transferevent = pyevent.RichRemoteFileTransferEvent(caller = None)
	transferevent.begin(
		files = from_paths,
		from_fs = from_fs,
		to_fs = to_fs
	)
	# if type(to_fs) == SSH and type(from_fs) == local -> scp.put ; type(from_fs) == SSH and type(to_fs) == local -> scp.get
	# else : not implemented
	scp = None
	if type(from_fs).__name__ ==  'RemoteSSHFileSystem' and type(to_fs).__name__ ==  'LocalFileSystem' and _CMDEXEC_REMOTE_ENABLED_:
		scp = SCPClient(from_fs.sshcon.get_transport(), progress = transferevent.progress)
		for file in from_paths:
			# Download file, for some reason scp.get only works with a single file contrary to scp.put
			scp.get(remote_path = file, recursive = False, local_path = to_path)

	elif type(from_fs).__name__ ==  'LocalFileSystem' and type(to_fs).__name__ ==  'RemoteSSHFileSystem' and _CMDEXEC_REMOTE_ENABLED_:
		scp = SCPClient(to_fs.sshcon.get_transport(), progress = transferevent.progress)
		# Upload files
		scp.put(files = from_paths, recursive = False, remote_path = to_path)
	else:
		raise RuntimeError(f"Transfer between {type(from_fs)} and {type(to_fs)} is not supported.")

	transferevent.end()
	if scp is not None:
		scp.close()


def transfer_dir(from_dirpath:str, to_dirpath:str, from_fs:FileSystem, to_fs:FileSystem):
	"""
	Transfert a DIRECTORY from one filesystem to a directory in another one
	Args:
		from_dirpath (str): Directory path in 'from_fs' filesystem
		to_dirpath (str): Directory path in 'to_fs' filesystem
		from_fs (FileSystem): Filesystem to transfert from
		to_fs (FileSystem): Filesystem to transfert to
	"""

	def transfer_node(node:FileSystemTree, to_dirpath:str, from_fs:FileSystem, to_fs:FileSystem):
		# Check if the dir already exists in 'to_fs'
		if to_fs.isdir(to_dirpath):
			to_fs.rmdir(to_dirpath, recur = True)
		to_fs.mkdir(to_dirpath, exist_ok = True)
		# Transfert files in the root of node
		transfer_files(
			from_paths = node.realfiles(),
			to_path = to_dirpath,
			from_fs = from_fs,
			to_fs = to_fs
		)

	# Format path according to their filesystems
	from_dirpath = from_fs.abspath(from_dirpath)
	to_dirpath = to_fs.abspath(to_dirpath)

	# Make sure that source and destinations are valid dir paths
	assert from_fs.isdir(from_dirpath)
	assert to_fs.isdir(to_dirpath)

	# from_dirpath in 'to_fs'
	todir = to_fs.join(to_dirpath, from_fs.basename(from_dirpath))
	# Check if the dir already exists in 'to_fs'
	if to_fs.isdir(todir):
		to_fs.rmdir(todir, recur = True)
	to_fs.mkdir(todir, exist_ok = True)

	# Inpect directory 'from_dirpath' inside 'from_fs'
	from_tree:FileSystemTree = from_fs.lsdir(from_dirpath)
	for node in from_tree.nodes():
		# Get node root dir path in destination filesystem
		node_fromdir = to_fs.convert(to_fs.join(todir, node.relative_to_root()))
		transfer_node(
			node = node,
			to_dirpath = node_fromdir,
			from_fs = from_fs,
			to_fs = to_fs
		)

def transfer(
	from_path:str, 
	to_path:str, 
	from_fs:FileSystem, 
	to_fs:FileSystem,
	compress_before:bool = False,
	uncompress_after:bool = False):
	"""
	Transfert a file or directory from one filesystem to a directory in another one
	Args:
		from_path (str): Path in 'from_fs' filesystem
		to_path (str): Path in 'to_fs' filesystem
		from_fs (FileSystem): Filesystem to transfert from
		to_fs (FileSystem): Filesystem to transfert to
		compress_before (bool, optional): Compress the file or folder in 'from_fs' before transfer to 'to_fs'. Defaults to False.
		uncompress_after (bool, optional): Uncompress the file or folder in 'to_fs' after transfer. Defaults to False.
	"""
	if compress_before:
		# Compress file or folder in 'from_fs'
		archivename_from= from_fs.zip(path = from_path)
		# transfer it as a file
		transfer_files([archivename_from], to_path, from_fs, to_fs)
		# Remove archive created in 'from_fs'
		from_fs.unlink(archivename_from)
		
		if uncompress_after:
			# Get archive name is destination 'to_fs' filesystem
			archivename_to = to_fs.join(to_path, from_fs.basename(archivename_from))
			# Uncompress transfered archive in 'to_fs' filesystem
			to_fs.unzip(archivename_to)
			# Remove transfered archive from 'to_fs' filesystem
			to_fs.unlink(archivename_to)
		return

	# Default transfert case
	if from_fs.isfile(from_path):
		transfer_files([from_path], to_path, from_fs, to_fs)
	elif from_fs.isdir(from_path):
		transfer_dir(from_path, to_path, from_fs, to_fs)
	else:
		raise RuntimeError(f"Path {from_path} is not a valid path")