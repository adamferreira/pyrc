import paramiko
import getpass
from scp import SCPClient, SCPException
import pyrc.event.event as pyevent
from pyrc.system.filesystem import FileSystem

# ------------------ RemoteSSHFileSystem
class RemoteSSHFileSystem(FileSystem):

	@property
	def hostname(self) -> str:
		return self._hostname

	@property
	def proxycommand(self) -> str:
		return self._proxycommand

	@property
	def use_proxy(self) -> bool:
		return self._proxycommand is not None and self._proxycommand != ""

	@property
	def user(self) -> str:
		return str(self._user)

	@property
	def sshkey(self) -> str:
		return str(self._sshkey)

	@property
	def port(self) -> int:
		return str(self._port)

	@property
	def askpwd(self) -> bool:
		return self._askpwd
	@askpwd.setter
	def askpwd(self, askpwd):
		self._askpwd = askpwd


	def __init__(self, user:str, hostname:str, sshkey:str, port:int = None, proxycommand:str = None, askpwd:bool = False) -> None:
		self._user:str = user
		self._hostname:str = hostname
		self._proxycommand:str = proxycommand
		self._sshkey:str = sshkey
		self._port:int = port
		self._askpwd:bool = askpwd
		self._sshcon = None
		self._scp = None

		# Creating remote connection
		self._sshcon = paramiko.SSHClient()  # will create the object
		# Setting up proxy
		self._sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error

		# Events
		self.__filesupload_event = pyevent.RichRemoteFileTransferEvent(self)
		self.__dirupload_event = pyevent.RichRemoteDirUploadEvent(self)
		self.__filesdownload_event = pyevent.FileTransferEvent(self)
		self.__dirdownload_event = pyevent.RichRemoteDirDownloadEvent(self)
		

	def __del__(self):
		self.close()

	def open(self, password:str = None, passphrase:str = None) -> None:
		"""
			Opens the remote connection.
		"""
		proxy = paramiko.ProxyCommand(self.proxycommand) if self.use_proxy else None
		pwd = getpass.getpass(prompt=f"Password for {self.user}@{self.hostname}:") if self.askpwd else password

		self._sshcon.connect(
						self.hostname, 
						username=self.user, 
						port=self.port,
						key_filename=self.sshkey, 
						password=pwd,
						passphrase=passphrase,
						sock=proxy
					)

		# SCP connection
		self._scp = SCPClient(self._sshcon.get_transport())
		# Deduce os from new connection
		FileSystem.__init__(self)

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
		if environment is not None:
			if self.path.is_unix():
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
		output = self.check_output("python -c \"import platform; print(platform.system()); print(platform.release())\"")
		return { "system" : output[0], "release" : output[1] }

# ------------------ RemoteSSHFileSystem