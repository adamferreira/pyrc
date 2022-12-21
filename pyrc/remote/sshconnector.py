import getpass
import pyrc.event.event as pyevent
from pyrc.remote.transfer import transfer
from pyrc.system.command import FileSystemCommand
from pyrc.system.local import LocalFileSystem

try:
	import paramiko
	from scp import SCPClient, SCPException
	_CMDEXEC_REMOTE_ENABLED_ = True
except BaseException as err:
	_CMDEXEC_REMOTE_ENABLED_ = False

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
		# Setting up proxy
		self._sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error

		# Will be set later
		self.environ = {}
		
	def __eq__(self, other):
		"""Two RemoteSSHFileSystem are considered equals if they have the same config"""
		return (type(self).__name__ == type(other).__name__) and (self._kwargs == other._kwargs) 

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

		# Deduce os from new connection
		FileSystemCommand.__init__(self)

	def close(self) -> None:
		"""
			Close remote connection.
		"""
		if self._sshcon:
			self._sshcon.close()

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
		environment = {} if environment is None else self.environ
		stdin, stdout, stderr = self.__exec_command(cmd, cwd, environment)
		# Blocking event
		# TODO: Unify default event for all connectors ?
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
		output = self.evaluate("python3 -c \"import platform; print(platform.system()); print(platform.release())\"")
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
