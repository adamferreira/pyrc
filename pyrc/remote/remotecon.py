import paramiko
from scp import SCPClient, SCPException
import logging
import getpass
import pyrc.event.progress as pyprogress
import pyrc.event.event as pyevent
import pyrc.local
import os, rich
from pathlib import Path

def strip_stdout(stdout):
	return stdout.read().decode("utf-8").strip('\n').split('\n')	

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
	def unix(self) -> bool:
		return self._isunix


	def __init__(self, user:str, hostname:str, sshkey:str, proxycommand:str = None, askpwd:bool = False):
		self._user:str = user
		self._hostname:str = hostname
		self._proxycommand:str = proxycommand
		self._sshkey:str = sshkey
		self._askpwd:bool = askpwd
		self._environ:SSHConnector.SSHEnvironDict = None
		self._isunix:bool = None
		self._cwd:str = "" # Currend directory
		self._sshcon = None
		self._scp = None

		# Creating remote connection
		self._sshcon = paramiko.SSHClient()  # will create the object
		# Setting up proxy
		self._sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error


	def exec_command(self, cmd:str, print_output:bool = False, print_input:bool = False):
		"""[summary]
			Execute the given command line on the remote machine.
		Args:
			cmd (str): Command line to execute.
			print_output (bool, optional): Boolean to print or not remote stdout to local stdout]. Defaults to False.

		Returns:
			stdin, stdout, stderr: stdin, stdout, stderr
		"""
		if print_input:
			print("[" + self.user + "@" + self.hostname + "]", cmd)
		stdin, stdout, stderr = self._sshcon.exec_command("cd " + self._cwd + ";" + cmd)
		#stdout.channel.recv_exit_status()
		if print_output:
			for line in stdout.readlines():
				print("[" + self.user + "@" + self.hostname + "] ->", line)
		
		return stdin, stdout, stderr

	def check_output(self, cmd:str):
		_, stdout, _ = self.exec_command(cmd, print_output=False, print_input=False)
		return strip_stdout(stdout)

	def open(self):
		"""[summary]
			Opens the remote connection.
		"""
		if self.use_proxy:
			proxy = paramiko.ProxyCommand(self.proxycommand)
			self._sshcon.connect(self.hostname, username=self.user, key_filename=self.sshkey, sock=proxy)
		else:
			if self.askpwd:
				self._sshcon.connect(
					self.hostname, 
					username=self.user, 
					key_filename=self.sshkey, 
					password=getpass.getpass(prompt=f"Password for {self.user}@{self.hostname}:"))
			else:
				self._sshcon.connect(self.hostname, username=self.user, key_filename=self.sshkey)

		# SCP connection
		self._scp = SCPClient(self._sshcon.get_transport())
		# Load remote env vars
		self._environ = SSHConnector.SSHEnvironDict(self)
		# Load remote system informations 
		self._isunix = self.platform()["system"] != "Windows"

	def is_open(self):
		return self._sshcon.get_transport().is_active()

	def is_unix(self) -> bool:
		return self._isunix

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
		stdin, stdout, stderr = self.exec_command("ls " + folderpath)
		for file in stdout.readlines():
			outlist.append(file.replace('\n', ''))
		return outlist

	def join(self, *args):
		return '/'.join(args) if self.unix else '\\'.join(args)


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
		event = pyevent.FileProgressEvent(self, local_paths)
		event.transfer_begin()
		scp = SCPClient(self._sshcon.get_transport(), progress = event.progress)
		scp.put(local_paths, recursive=False, remote_path = remote_path)
		event.transfer_end()
		scp.close()
	
	def __upload_folder(self, local_realdir:str, dir_prefix:str, folder_files:'List[str]', remote_path:str):
		"""[summary]

		Args:
			local_realdir (str): [description]
			dir_prefix (str): [description]
			folder_files (List[str]): [description]
			remote_path (str): [description]
		"""
		remote_path = self.join(remote_path, dir_prefix)
		if self.remote_file_exists(remote_path):
			self.rm(remote_path)
		self.mkdir(remote_path)

		rich.print(f"Uploading directory {local_realdir} to {self.user}@{self.hostname}:{remote_path}")
		self.__upload_files(local_paths=[os.path.join(local_realdir, file) for file in folder_files], remote_path=remote_path)

	def __upload_tree(self, directory_realpath:str, remote_path:str):
		"""[summary]

		Args:
			directory_realpath (str): [description]
			remote_path (str): [description]
		"""
		tree = pyrc.local.system.list_all_recursivly(directory_realpath)
		for directory in tree:
			dir_commom = os.path.commonprefix([Path(directory_realpath).parent.absolute(), directory])
			self.__upload_folder(
				local_realdir = directory,
				dir_prefix = os.path.relpath(directory, dir_commom),
				folder_files = tree[directory],
				remote_path = remote_path
			)

	def upload(self, local_realpath:str, remote_path:str):
		"""[summary]

		Args:
			local_realpath (str): [description]
			remote_path (str): [description]
		"""
		local_realpath = os.path.realpath(local_realpath)
		if os.path.isdir(local_realpath):
			self.__upload_tree(local_realpath, remote_path)
		if os.path.isfile(local_realpath):
			self.__upload_files([local_realpath], remote_path)
		

	def upload1(self, local_file, remote_path = None):
		#remote_path = remote_path if remote_path is not None else self._cwd
		#look = pyrc.local.system.list_all_recursivly(local_file)
		#print(look)
		#total = sum([sum([os.path.getsize(os.path.join(folder, f)) for f in look[folder]]) for folder in look])
		#print(total, pyrc.local.system.get_size(local_file))	
		#return
		#progress.start()
		#progress.update(task_id, total=os.path.getsize(local_file))
		#progress.start_task(task_id)
		start = time.time()
		print("Uploading", local_file, "...")
		upload = None
		try:
			self._scp.put(
				local_file,
				recursive=True,
				remote_path = remote_path
			)
			upload = local_file
		except SCPException as error:
			#logger.error(error)
			print(error)
			raise error
		finally:
			#logger.info(f'Uploaded {file} to {self.remote_path}')
			end = time.time()
			print(end - start)
			print("Uploaded", local_file, "to", remote_path)
			#progress.console.log(f"Uploaded {local_file}")
			#progress.stop()
			return upload

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
		stdin, stdout, stderr = self.exec_command("rm " + flag + " " + remote_path)

	def mkdir(self, remote_path):
		stdin, stdout, stderr = self.exec_command("mkdir " + remote_path)

	def zip(self, remote_path, remote_archive, flag = ""):
		stdin, stdout, stderr = self.exec_command("zip " + flag + " \"" + remote_archive + "\" \"" + remote_path + "\"", print_output = True)
		#stdin, stdout, stderr = self.exec_command("zip " + flag + " " + remote_archive + " " + remote_path, print_output = True)

	def unzip(self, remote_archive, remote_path, flag = ""):
		stdin, stdout, stderr = self.exec_command("unzip " + flag + " \"" + remote_archive + "\" -d \"" + remote_path + "\"", print_output = True)

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