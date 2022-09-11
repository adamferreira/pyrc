import pyrc.event.event as pyevent
from pyrc.system.filesystemtree import FileSystemTree
from pyrc.system.filesystem import OSTYPE, FileSystem
from pyrc.system.local import LocalFileSystem

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
	Returns:
		The new paths on 'to_fs' created by the transfer.
	"""

	def uncompatibility(from_fs:FileSystem, to_fs:FileSystem):
		return RuntimeError(f"Transfer between {type(from_fs).__name__} and {type(to_fs).__name__} is not supported.")

	# Format path according to their filesystems
	from_paths = [from_fs.abspath(from_path) for from_path in from_paths]
	to_path = to_fs.abspath(to_path)
	# Decudes new paths on destination filesystem 'to_fs'
	to_paths = [to_fs.join(to_path, from_fs.basename(from_path)) for from_path in from_paths]

	transferevent = pyevent.RichRemoteFileTransferEvent(caller = None)
	transferevent.begin(
		files = from_paths,
		from_fs = from_fs,
		to_fs = to_fs
	)

	# Special case where the two filesystems are identical
	# In that case just call copy
	if from_fs == to_fs:
		[from_fs.copy(from_path, to_path) for from_path in from_paths]
		transferevent.end()
		return to_paths

	# Special case if one of the two filesystems are a RemoteSSHFileSystem
	# if type(to_fs) == SSH and type(from_fs) == local -> scp.put ; type(from_fs) == SSH and type(to_fs) == local -> scp.get
	# else : not implemented
	if (type(from_fs).__name__ ==  'RemoteSSHFileSystem' or type(to_fs).__name__ ==  'RemoteSSHFileSystem') and _CMDEXEC_REMOTE_ENABLED_:
		scp = None
		if type(from_fs).__name__ ==  'RemoteSSHFileSystem' and type(to_fs).__name__ ==  'LocalFileSystem':
			scp = SCPClient(from_fs.sshcon.get_transport(), progress = transferevent.progress)
			for file in from_paths:
				# Download file, for some reason scp.get only works with a single file contrary to scp.put
				scp.get(remote_path = file, recursive = False, local_path = to_path)

		elif type(from_fs).__name__ ==  'LocalFileSystem' and type(to_fs).__name__ ==  'RemoteSSHFileSystem':
			scp = SCPClient(to_fs.sshcon.get_transport(), progress = transferevent.progress)
			# Upload files
			scp.put(files = from_paths, recursive = False, remote_path = to_path)
		else:
			raise uncompatibility(from_fs, to_fs)

		if scp is not None:
			scp.close()
		transferevent.end()
		return to_paths

	# Default case : uncompatibility
	raise uncompatibility(from_fs, to_fs)


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
	uncompress_after:bool = False,
	from_path_delete:bool = False):
	"""
	Transfert a file or directory from one filesystem to a directory in another one.
	Args:
		from_path (str): Path in 'from_fs' filesystem
		to_path (str): Path in 'to_fs' filesystem
		from_fs (FileSystem): Filesystem to transfert from
		to_fs (FileSystem): Filesystem to transfert to
		compress_before (bool, optional): Compress the file or folder in 'from_fs' before transfer to 'to_fs'. Defaults to False.
		uncompress_after (bool, optional): Uncompress the file or folder in 'to_fs' after transfer. Defaults to False.
		from_path_delete (bool, optional): Delete the file or folder in 'from_fs' after transfer. Defaults to False.
	Returns:
		The 'sent' path (depending it as been compressed or not beforehand).
		The 'received' path (depending it as been uncompressed or not afterwards).
	"""
	sent, reveiced = None, None
	# Files to be remove from 'from_fs' after the transfer completion
	from_fs_to_remove = []
	# Files to be remove from 'to_fs' after the transfer completion
	to_fs_to_remove = []

	# If 'compress_before' is selected, from_path becomes an archive (and thus a file)
	# If 'uncompress_after' is not selected, 'sent' is an archive (and thus a file)
	if compress_before:
		# Compress file or folder in 'from_fs'
		archivename_from = from_fs.zip(path = from_path)
		# transfer it as a file
		archivename_to = transfer_files([archivename_from], to_path, from_fs, to_fs)[0]
		# Remove archive created in 'from_fs'
		from_fs.unlink(archivename_from)
		
		if uncompress_after:
			# Uncompress transfered archive in 'to_fs' filesystem
			to_fs.unzip(archivename_to)
			# Remove transfered archive from 'to_fs' filesystem
			to_fs.unlink(archivename_to)
			return archivename_from, to_fs.join(to_path, from_fs.basename(from_path))

		return archivename_from, archivename_to
			

	# Default transfert case
	if from_fs.isfile(from_path):
		reveiced = transfer_files([from_path], to_path, from_fs, to_fs)[0]
		# Delete 'from_path' is 'from_fs' if requested
		if from_path_delete:
			from_fs.rm(from_path, recur = True)
		return from_path, reveiced

	elif from_fs.isdir(from_path):
		transfer_dir(from_path, to_path, from_fs, to_fs)
		# Delete 'from_path' is 'from_fs' if requested
		if from_path_delete:
			from_fs.rm(from_path, recur = True)
		return from_path, to_fs.join(to_path, from_fs.basename(from_path))

	else:
		raise RuntimeError(f"Path {from_path} is not a valid path")



#If neither from_fs or to_fs is 'LocalFileSystem', this perform a buffered transfer.
#The workflow will be the following from_fs -> LocalFileSystem -> to_fs
def __buffered_transfer(
	from_path:str, 
	to_path:str,
	local_buffer_path:str,
	from_fs:FileSystem, 
	to_fs:FileSystem,
	compress_before:bool = False,
	uncompress_after:bool = False,
	from_path_delete:bool = False):

	# Buffer must be a valid directory
	assert LocalFileSystem().isdir(local_buffer_path)

	# Transfer from 'from_ts' to local buffer
	sent, received = transfer(
		from_path = from_path,
		to_path = local_buffer_path,
		from_fs = from_fs,
		to_fs = LocalFileSystem(),
		compress_before = compress_before,
		uncompress_after = False,
		from_path_delete = from_path_delete
	)

	# Transfer from local buffer to 'to_fs'
	# Get 'from_path' equivalent in the buffered path
	# And remove local buffer content
	transfer(
		from_path = received,#LocalFileSystem().join(local_buffer_path, from_fs.basename(from_path)),
		to_path = to_path,
		from_fs = LocalFileSystem(),
		to_fs = to_fs,
		compress_before = False,
		uncompress_after = uncompress_after,
		from_path_delete = True
	)

if __name__ == "__main__":
	local = LocalFileSystem()
	A = local.join(local.join("C:\\", "Users", "adamf", "Downloads", "tmp", "A"))
	buff  = local.join(local.join("C:\\", "Users", "adamf", "Downloads", "tmp", "buffer"))
	B = _from = local.join(local.join("C:\\", "Users", "adamf", "Downloads", "tmp", "B"))
	assert local.isdir(A) and local.isdir(buff) and local.isdir(B)
	assert local.isfile(local.join(A, "to_move.txt"))
	__buffered_transfer(
		local.join(A, "to_move.txt"),
		B,
		buff,
		local,
		local,
		compress_before = True,
		uncompress_after = True,
		from_path_delete = False
	)