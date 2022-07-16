import paramiko
import getpass
from scp import SCPClient, SCPException
import pyrc.event.event as pyevent
from pyrc.system.command import FileSystemCommand
from pyrc.system.filesystemtree import FileSystemTree
from pyrc.system.filesystem import OSTYPE

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
		# Setting up proxy
		self._sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error

		# Events
		self.__filesupload_event = pyevent.RichRemoteFileTransferEvent(self)
		self.__dirupload_event = pyevent.RichRemoteDirUploadEvent(self)
		self.__filesdownload_event = pyevent.FileTransferEvent(self)
		self.__dirdownload_event = pyevent.RichRemoteDirDownloadEvent(self)

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

	def check_output(self, cmd:str,  environment:dict = None):
		return self.exec_command(cmd = cmd, environment = environment, event = pyevent.ErrorRaiseEvent(self))[0]

	# ------------------------
	#		Overrides
	# ------------------------

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
	def __upload_files(self, local_paths:'List[str]', remote_path:str):
		"""

		Args:
			local_paths (List[str]): Absolute file paths
			remote_path (str): Absolute remote path
		"""
		self.filesupload_event.begin(local_paths)
		scp = SCPClient(self._sshcon.get_transport(), progress = self.filesupload_event.progress)
		scp.put(local_paths, recursive=False, remote_path = remote_path)
		self.filesupload_event.end()
		scp.close()
	
	def __upload_node(self, localnode:FileSystemTree, remote_path:str):
		"""

		Args:
			localnode (FileSystemTree): [description]
			remote_path (str): [description]
		"""

		if self.remote_file_exists(remote_path):
			self.rm(remote_path)
		self.mkdir(remote_path, exist_ok=True)

		self.dirupload_event.begin(localnode.realpath(), remote_path)
		self.__upload_files(local_paths=localnode.realfiles(), remote_path=remote_path)
		self.dirupload_event.end()

	def __upload_tree(self, localtree:FileSystemTree, remote_path:str):
		for n in localtree.nodes():
			self.__upload_node(localnode = n, remote_path = self.join(remote_path, n.relpath()))
			

	def upload(self, local_realpath:str, remote_path:str):
		"""

		Args:
			local_realpath (str): [description]
			remote_path (str): [description]
		"""
		local_realpath = os.path.realpath(local_realpath)
		if os.path.isdir(local_realpath):
			self.__upload_tree(FileSystemTree.get_tree(local_realpath), remote_path)

		if os.path.isfile(local_realpath):
			self.__upload_files([local_realpath], remote_path)

	def __download_files(self, remote_paths:'List[str]', local_path:str):
		"""

		Args:
			remote_paths (List[str]): Absolute remote paths
			local_path (str): Absolute local path
		"""
		self.__filesdownload_event.begin(remote_paths)
		scp = SCPClient(self._sshcon.get_transport(), progress = self.__filesdownload_event.progress)
		scp.get(local_path = local_path, recursive=False, remote_path = remote_paths)
		self.__filesdownload_event.end()
		scp.close()

	def download(self, remote_file_path, local_file_path = "."):
		"""Recursivly download files/folder from remote host.

		Args:
			file ([remote_file_path]): Remote file path.
		"""
		print("Downloading", remote_file_path, "...")
		try:
			self._scp.get(remote_path = remote_file_path, local_path = local_file_path, recursive=True)
		except SCPException as error:
			print(error)
			raise error
		finally:
			print("Downloaded", remote_file_path, "to", local_file_path)

	def zip(self, remote_path, remote_archive, flag = ""):
		stdin, stdout, stderr = self.__exec_command("zip " + flag + " \"" + remote_archive + "\" \"" + remote_path + "\"", print_output = True)

	def unzip(self, remote_archive, remote_path, flag = ""):
		stdin, stdout, stderr = self.__exec_command("unzip " + flag + " \"" + remote_archive + "\" -d \"" + remote_path + "\"", print_output = True)

	def compress_folder(self, remote_folder_path, sep = "/"):
		return NotImplemented
		if self.remote_file_exists(remote_folder_path):
			tmpwd = self._cwd
			self.cd(remote_folder_path)
			splitt = remote_folder_path.split(sep)
			remote_archive = splitt[len(splitt)-1] + ".zip"
			self.zip(".", remote_archive, flag = "-r")
			self.cd(tmpwd)
			return remote_folder_path + sep + remote_archive
		else:
			raise RuntimeError("Remote folder " + remote_folder_path + " not found.")

	def download_folder(self, remote_folder_path, local_path, compress = False, clean_remote = False):
		if os.path.isdir(local_path):
			raise RuntimeError("Local path already exists !")

		if self.remote_file_exists(remote_folder_path):
			if compress:
				remote_archive_path = self.compress_folder(remote_folder_path)
				self.download(remote_archive_path, local_path + ".zip")
				self.rm(remote_archive_path, "-r")
			else:
				self.download(remote_folder_path, local_path)

			if clean_remote:
				self.rm(remote_folder_path, "-r")
		else:
			raise RuntimeError("Remote folder " + remote_folder_path + " cannot be found on " + self._hostname + ".")
# ------------------ RemoteSSHFileSystem