from genericpath import isdir, isfile
from charset_normalizer import from_path
import paramiko
import getpass
from scp import SCPClient, SCPException
import pyrc.event.event as pyevent
from pyrc.system.command import FileSystemCommand
from pyrc.system.filesystemtree import FileSystemTree
from pyrc.system.filesystem import OSTYPE, FileSystem
from pyrc.system.local import LocalFileSystem


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
			print(archivename_to)
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
	

# ------------------ RemoteSSHFileSystem
class RemoteSSHFileSystem(FileSystemCommand):
	"""
	RemoteSSHFileSystem will submit evey generated command (FileSystemCommand)
	to a remote machine throuth a SSH connection
	"""

	@property
	def hostname(self) -> str:
		return self._kwargs["hostname"]

	@property
	def proxy(self) -> str:
		return self._kwargs["proxy"]

	@property
	def user(self) -> str:
		return self._kwargs["username"]

	@property
	def port(self) -> int:
		return self._kwargs["port"]

	@property
	def askpwd(self) -> bool:
		return self._kwargs["askpwd"]

	@property
	def sshcon(self) -> paramiko.SSHClient:
		return self._sshcon

	#@overrides
	def is_unix(self) -> bool:
		return True

	def __init__(self, **kwargs) -> None:
		"""
		See https://docs.paramiko.org/en/stable/api/client.html
		Parameters:	
		hostname (str) – the server to connect to
		port (int) – the server port to connect to
		username (str) – the username to authenticate as (defaults to the current local username)
		password (str) – Used for password authentication; is also used for private key decryption if passphrase is not given.
		passphrase (str) – Used for decrypting private keys.
		pkey (PKey) – an optional private key to use for authentication
		key_filename (str) – the filename, or list of filenames, of optional private key(s) and/or certs to try for authentication
		timeout (float) – an optional timeout (in seconds) for the TCP connect
		allow_agent (bool) – set to False to disable connecting to the SSH agent
		look_for_keys (bool) – set to False to disable searching for discoverable private key files in ~/.ssh/
		compress (bool) – set to True to turn on compression
		sock (socket) – an open socket or socket-like object (such as a Channel) to use for communication to the target host
		gss_auth (bool) – True if you want to use GSS-API authentication
		gss_kex (bool) – Perform GSS-API Key Exchange and user authentication
		gss_deleg_creds (bool) – Delegate GSS-API client credentials or not
		gss_host (str) – The targets name in the kerberos database. default: hostname
		gss_trust_dns (bool) – Indicates whether or not the DNS is trusted to securely canonicalize the name of the host being connected to (default True).
		banner_timeout (float) – an optional timeout (in seconds) to wait for the SSH banner to be presented.
		auth_timeout (float) – an optional timeout (in seconds) to wait for an authentication response.
		disabled_algorithms (dict) – an optional dict passed directly to Transport and its keyword argument of the same name.
		Raises:	
		BadHostKeyException – if the server’s host key could not be verified

		Raises:	
		AuthenticationException – if authentication failed

		Raises:	
		SSHException – if there was any other error connecting or establishing an SSH session

		Raises:	
		socket.error – if a socket error occurred while connecting
		"""
		self._kwargs:dict = dict(kwargs)

		# Creating remote connection
		self._sshcon = paramiko.SSHClient()  # will create the object
		self._scp = None # set in 'open()'
		# Setting up proxy
		self._sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error

		# Will be set later
		self.environ = {}
		

	def __del__(self):
		self.close()

	def open(self) -> None:
		"""
			Opens the remote connection.
		"""
		askpwd = False
		args = dict(self._kwargs)
		if "askpwd" in args:
			# Remove non paramiko params
			askpwd = args["askpwd"]
			del args["askpwd"]

		if askpwd:
			args["password"] = getpass.getpass(prompt=f"Password for {self.user}@{self.hostname}:")

		if "proxycommand" in args:
			args["sock"] = paramiko.ProxyCommand(args["proxycommand"])
			# Remove non paramiko params
			del args["proxycommand"]
		
		self._sshcon.connect(**args)

		# SCP connection
		self._scp = SCPClient(self._sshcon.get_transport())
		# Deduce os from new connection
		FileSystemCommand.__init__(self)

	def close(self) -> None:
		"""
			Close remote connection.
		"""
		if self._sshcon:
			self._sshcon.close()
		if self._scp:
			self._scp.close()

	def __exec_command(self, cmd:str, cwd:str = "", environment:dict = None):
		env_vars = ""
		if environment is not None and len(environment) > 0:
			if self.is_unix():
				env_vars = ';'.join([f"export {var}={environment[var]}" for var in environment.keys()]) + ";"
			else:
				raise NotImplemented("Cannot set environment variables for Windows remote systems")

		stdin, stdout, stderr = self._sshcon.exec_command(env_vars + "cd " + cwd + ";" + cmd, environment = environment, get_pty=False)
		return stdin, stdout, stderr

	# ------------------------
	#		Overrides
	# ------------------------

	#@overrides
	def name(self) -> str:
		return f"{self.user}@{self.hostname}"

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		environment = {} if environment is None else dict(environment)
		environment.update(self.environ)
		stdin, stdout, stderr = self.__exec_command(cmd, cwd, environment)
		# Blocking event
		event = pyevent.CommandPrettyPrintEvent(self, print_input=True, print_errors=True) if event is None else event
		event.begin(cmd, cwd, stdin, stdout, stderr)
		return event.end()

	#@overrides
	def is_remote(self) -> bool:
		return True

	#@overrides
	def is_open(self) -> bool:
		return self._sshcon.get_transport().is_active()

	#@overrides
	def platform(self) -> 'dict[str:str]':
		"""
		Uses python packages 'platform' on remote host to retrieve system informations
		The information exactly what 'platform.system()' and 'platform.release()' returns
		Raises:
			RuntimeError
		Returns:
			[dict[str:str]]: A dict of remote system informations. Keys are 'system' and 'release'
		"""
		output = self.check_output("python3 -c \"import platform; print(platform.system()); print(platform.release())\"")
		return { "system" : output[0], "release" : output[1] }

	# --------------------------------------------------
	def upload(self, from_path:str, to_path:str, compress_before:bool = False, uncompress_after:bool = False):
		"""
		Upload a file or directory from local filesystem to the remote filesystem through SSH
		Args:
			from_dirpath (str): Path of file or directory locally 
			to_dirpath (str): Path to a directory in the remote filesystem
			compress_before (bool, optional): Compress the file or folder locally before transfert. Defaults to False.
			uncompress_after (bool, optional): Uncompress the file or folder in remote machine after transfer. Defaults to False.
		"""
		transfer(
			from_path = from_path,
			to_path = to_path,
			from_fs = LocalFileSystem(),
			to_fs = self,
			compress_before = compress_before,
			uncompress_after = uncompress_after
		)

			
	def download(self, from_path:str, to_path:str, compress_before:bool = False, uncompress_after:bool = False):
		"""
		Download a file or directory from remote filesystem through SSH to the local filesystem
		Args:
			from_dirpath (str): Path of file or directory in the remote filesystem
			to_dirpath (str): Path to a local directory 
			compress_before (bool, optional): Compress the file or folder remotly before transfert. Defaults to False.
			uncompress_after (bool, optional): Uncompress the file or folder locally after transfer. Defaults to False.
		"""
		transfer(
			from_path = from_path,
			to_path = to_path,
			from_fs = self,
			to_fs = LocalFileSystem(),
			compress_before = compress_before,
			uncompress_after = uncompress_after
		)



# ------------------ RemoteSSHFileSystem
