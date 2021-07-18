import paramiko
from scp import SCPClient, SCPException
import logging
import getpass
import pyrc.event.progress as pyprogress
import pyrc.event.event as pyevent
from pyrc.system.system import FileSystem, FileSystemTree
import os
from pathlib import Path, PosixPath, PureWindowsPath, PurePosixPath, WindowsPath


# ------------------ SSHConnector
class SSHConnector:

	class SSHEnvironDict(dict[str:str]):
		# if the connection is alredy open, we get all remote env vars
		def __init__(self, remote):
			self.remote = remote
			if self.remote is not None and self.remote.is_open():
				self.__load_env()

		# If a var is already in the dict (assumed loaded from remote)
		# We return is at is is
		# Otherwise it is loaded from remote and stored in the dict
		def __getitem__(self, key:str):
			# Get cached key if entry exists
			if key in self:
				return super().__getitem__(key)
			else:
				super().__setitem__(key, self.remote._env(key))
				return super().__getitem__(key)

		# Get all remote env vars
		def __load_env(self):
			remoteenvs = self.remote._printenv()
			for key,val in remoteenvs.items():
				super().__setitem__(key, val)


	""" 
		MEMBERS
	"""
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
	def pwd(self):
		return self._cwd
	def cd(self, directory:str):
		self._cwd = directory

	@property
	def askpwd(self) -> bool:
		return self._askpwd
	@askpwd.setter
	def askpwd(self, askpwd):
		self._askpwd = askpwd

	@property
	def environ(self) -> SSHEnvironDict:
		return self._environ

	@property
	def path(self) -> FileSystem:
		return self.__path

	@property 
	def filesupload_event(self):
		return self.__filesupload_event

	@property 
	def dirupload_event(self):
		return self.__dirupload_event

	@property 
	def filesdownload_event(self):
		return self.__filesdownload_event

	@property 
	def dirdownload_event(self):
		return self.__dirdownload_event

	@property
	def cmd_event(self):
		return self.__cmd_event


	def __init__(self, user:str, hostname:str, sshkey:str, port:int = None, proxycommand:str = None, askpwd:bool = False):
		self._user:str = user
		self._hostname:str = hostname
		self._proxycommand:str = proxycommand
		self._sshkey:str = sshkey
		self._port:int = port
		self._askpwd:bool = askpwd
		self._environ:SSHConnector.SSHEnvironDict = None
		self._cwd:str = "" # Currend directory
		self._sshcon = None
		self._scp = None

		# os related
		self.__path:FileSystem = None

		# Creating remote connection
		self._sshcon = paramiko.SSHClient()  # will create the object
		# Setting up proxy
		self._sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error


		# Events
		self.__filesupload_event = pyevent.RichRemoteFileTransferEvent(self)
		self.__dirupload_event = pyevent.RichRemoteDirUploadEvent(self)
		self.__filesdownload_event = pyevent.FileTransferEvent(self)
		self.__dirdownload_event = pyevent.RichRemoteDirDownloadEvent(self)
		self.__cmd_event = pyevent.CommandPrintEvent(self)

	def __exec_command(self, cmd:str):
		stdin, stdout, stderr = self._sshcon.exec_command("cd " + self._cwd + ";" + cmd)
		return stdin, stdout, stderr

	def exec_command(self, cmd:str, event:pyevent.Event = None):
		stdin, stdout, stderr = self.__exec_command("cd " + self._cwd + ";" + cmd)
		# Blocking event
		event = self.__cmd_event if event is None else event
		event.begin(cmd, stdin, stdout, stderr)
		return event.end()

	def check_output(self, cmd:str):
		return self.exec_command(cmd=cmd, event = pyevent.CommandStoreEvent(self))[0]

	def open(self):
		"""[summary]
			Opens the remote connection.
		"""
		if self.use_proxy:
			proxy = paramiko.ProxyCommand(self.proxycommand)
			self._sshcon.connect(self.hostname, username=self.user, port=self.port, key_filename=self.sshkey, sock=proxy)
		else:
			if self.askpwd:
				self._sshcon.connect(
					self.hostname, 
					username=self.user, 
					port=self.port,
					key_filename=self.sshkey, 
					password=getpass.getpass(prompt=f"Password for {self.user}@{self.hostname}:"))
			else:
				self._sshcon.connect(self.hostname, username=self.user, port=self.port, key_filename=self.sshkey)

		# SCP connection
		self._scp = SCPClient(self._sshcon.get_transport())
		# Load remote env vars
		self._environ = SSHConnector.SSHEnvironDict(self)
		
		# Load file system now that the connexion is open
		self.__path = FileSystem(self)
		

	def is_open(self):
		return self._sshcon.get_transport().is_active()

	def close(self):
		"""[summary]
			Close remote connection.
		"""
		if self._sshcon:
			self._sshcon.close()
		if self._scp:
			self._scp.close()

	def ls(self, folderpath):
		"""[summary]
			List all remote files and folder found in remote path 'folderpath'.
		Args:
			folderpath (str): Remote path to explore.

		Returns:
			list: List of all the remotes file names.
		"""
		outlist = []
		stdin, stdout, stderr = self.__exec_command("ls " + folderpath)
		for file in stdout.readlines():
			outlist.append(file.replace('\n', ''))
		return outlist

	def remote_file_exists_in_folder(self, folderpath, filename):
		return filename in self.ls(folderpath)

	def remote_file_exists(self, filepath) -> bool:
		splitt = filepath.split("/")
		filename = splitt[len(splitt)-1]
		folderpath = ""
		for p in splitt[:len(splitt)-1]:
			folderpath += str(p)+'/'

		return self.remote_file_exists_in_folder(folderpath, filename)

	def __upload_files(self, local_paths:'List[str]', remote_path:str):
		"""[summary]

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
		"""[summary]

		Args:
			localnode (FileSystemTree): [description]
			remote_path (str): [description]
		"""

		if self.remote_file_exists(remote_path):
			self.rm(remote_path)
		self.path.mkdir(remote_path, exist_ok=True)

		self.dirupload_event.begin(localnode.realpath(), remote_path)
		self.__upload_files(local_paths=localnode.realfiles(), remote_path=remote_path)
		self.dirupload_event.end()

	def __upload_tree(self, localtree:FileSystemTree, remote_path:str):
		for n in localtree.nodes():
			self.__upload_node(localnode = n, remote_path = self.path.join(remote_path, n.relpath()))
			

	def upload(self, local_realpath:str, remote_path:str):
		"""[summary]

		Args:
			local_realpath (str): [description]
			remote_path (str): [description]
		"""
		local_realpath = os.path.realpath(local_realpath)
		if os.path.isdir(local_realpath):
			self.__upload_tree(FileSystemTree.get_tree(local_realpath), remote_path)

		if os.path.isfile(local_realpath):
			self.__upload_files([local_realpath], remote_path)

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

	def rm(self, remote_path, flag = ""):
		stdin, stdout, stderr = self.__exec_command("rm " + flag + " " + remote_path)

	def zip(self, remote_path, remote_archive, flag = ""):
		stdin, stdout, stderr = self.__exec_command("zip " + flag + " \"" + remote_archive + "\" \"" + remote_path + "\"", print_output = True)

	def unzip(self, remote_archive, remote_path, flag = ""):
		stdin, stdout, stderr = self.__exec_command("unzip " + flag + " \"" + remote_archive + "\" -d \"" + remote_path + "\"", print_output = True)

	def compress_folder(self, remote_folder_path, sep = "/"):
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

	
	def platform(self) -> 'dict[str:str]':
		"""[summary]
		Uses python packages 'platform' on remote host to retrieve system informations
		The information exactly what 'platform.system()' and 'platform.release()' returns
		Raises:
			RuntimeError: [description]
		Returns:
			[dict[str:str]]: A dict of remote system informations. Keys are 'system' and 'release'
		"""
		output = self.check_output("python -c \"import platform; print(platform.system()); print(platform.release())\"")
		return { "system" : output[0], "release" : output[1] }

	def _env(self, var:str) -> str:
		return self.check_output(f"python -c \"import os; print(os.environ[\'{var}\'])\"")[0]

	def _printenv(self) -> dict[str:str]:
		# windows : out = return self.check_output("python -c \"import os; print(os.environ)\"")
		out = self.check_output("printenv")
		return {env.split("=")[0] : ''.join(env.split("=")[1:]) for env in out}
		

		

	

# ------------------ SSHConnector