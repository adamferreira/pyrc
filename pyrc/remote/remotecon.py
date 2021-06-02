import paramiko
from scp import SCPClient, SCPException
import logging
import os
import getpass

# ------------------ SSHConnector
class SSHConnector:

	def get_ssh_configurations(user_config_file:str) -> 'dict[str:dict[str:str]]':
		ssh_config = paramiko.SSHConfig.from_path(user_config_file)
		return {hostname : ssh_config.lookup(hostname) for hostname in ssh_config.get_hostnames()}


	def create_connectors(user_config_file:str, sshkey:str=None) -> 'dict[str:SSHConnector]':
		# Exception if file does not exist
		ssh_configs = SSHConnector.get_ssh_configurations(user_config_file)

		# If no sshkey specified we add one from the folder where the config file is
		if sshkey is None:
			sshkey = os.path.join(os.path.dirname(user_config_file), "id_rsa")
		
		connectors = {}
		for hostname in ssh_configs:
			if hostname == "*":
				continue
			
			# Creating user config dictionnary
			user_config = ssh_configs[hostname]
			connectors[hostname] = SSHConnector(
				hostname=hostname,
				user=user_config["user"],
				user_config_file=user_config_file,
				sshkey=sshkey,
				use_proxy="proxycommand" in user_config,
				askpwd = False
			)
		return connectors


	def __init__(self, hostname, user, user_config_file, sshkey, use_proxy:bool = False, askpwd = False):
		# Class members
		self.hostname = hostname
		self.user = user
		self.user_config_file = user_config_file
		self.sshkey = sshkey
		self.askpwd = askpwd
		self.use_proxy = use_proxy
		self.sshcon = None
		self.scp = None
		self.user_config = None

		# Currend directory
		self.cwd = ""

		# Creating remote connection
		self.sshcon = paramiko.SSHClient()  # will create the object
		ssh_config = paramiko.SSHConfig.from_path(self.user_config_file)

		# Creating user config dictionnary
		self.user_config = ssh_config.lookup(self.hostname)

		# Setting up proxy
		self.sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error


	def exec_command(self, cmd, print_output = False, print_input = True):
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
		stdin, stdout, stderr = self.sshcon.exec_command("cd " + self.cwd + ";" + cmd)
		#stdout.channel.recv_exit_status()
		if print_output:
			for line in stdout.readlines():
				print("[" + self.user + "@" + self.hostname + "] ->", line)
		
		return stdin, stdout, stderr

	def open(self, use_proxy:bool = None):
		"""[summary]
			Opens the remote connection.
		Args:
			use_proxy (bool): Specify if the remote connection should go through a proxy.
		"""
		if use_proxy is not None:
			self.use_proxy = use_proxy

		if self.use_proxy:
			proxy = paramiko.ProxyCommand(self.user_config["proxycommand"])
			self.sshcon.connect(self.user_config["hostname"], username=self.user, key_filename=self.sshkey, sock=proxy)
		else:
			if self.askpwd:
				self.sshcon.connect(
					self.user_config["hostname"], 
					username=self.user, 
					key_filename=self.sshkey, 
					password=getpass.getpass(prompt="Password for " + self.user + "@" + self.user_config["hostname"] + " : "))
			else:
				self.sshcon.connect(self.user_config["hostname"], username=self.user, key_filename=self.sshkey)

		# SCP connection
		self.scp = SCPClient(self.sshcon.get_transport())

	def is_open(self):
		try:
			self.open(self.use_proxy)
			return True
		except :
			return False
		
		return False

	def close(self):
		"""[summary]
			Close remote connection.
		"""
		if self.sshcon:
			self.sshcon.close()
		if self.scp:
			self.scp.close()

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

	def cd(self, directory):
		self.cwd = directory

	def pwd(self):
		return self.cwd

	def remote_file_exists_in_folder(self, folderpath, filename):
		return filename in self.ls(folderpath)

	def remote_file_exists(self, filepath):
		splitt = filepath.split("/")
		filename = splitt[len(splitt)-1]
		folderpath = ""
		for p in splitt[:len(splitt)-1]:
			folderpath += str(p)+'/'

		return self.remote_file_exists_in_folder(folderpath, filename)

	def upload(self, local_file, remote_path):
		print("Uploading", local_file, "...")
		upload = None
		try:
			self.scp.put(
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
			print("Uploaded", local_file, "to", remote_path)
			return upload		

	def upload_file(self, local_file):
		return self.upload(local_file, self.cwd)

	def download(self, remote_file_path, local_file_path = "."):
		"""Recursivly download files/folder from remote host.

		Args:
			file ([remote_file_path]): Remote file path.
		"""
		print("Downloading", remote_file_path, "...")
		try:
			self.scp.get(remote_path = remote_file_path, local_path = local_file_path, recursive=True)
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
			tmpwd = self.cwd
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
			raise RuntimeError("Remote folder " + remote_folder_path + " cannot be found on " + self.hostname + ".")

	
	def get_platform_infos(self) -> 'dict[str:str]':
		"""[summary]
		Uses python packages 'platform' on remote host to retrieve system informations
		The information exactly what 'platform.system()' and 'platform.release()' returns
		Raises:
			RuntimeError: [description]
		Returns:
			[dict[str:str]]: A dict of remote system informations. Keys are 'system' and 'release'
		"""
		pythoncmd = "python -c \"import platform; print(platform.system()); print(platform.release())\""
		stdin, stdout, stderr = self.exec_command(pythoncmd, print_output = False, print_input = False)
		errors = stderr.readlines()

		if len(errors) > 0:
			raise RuntimeError(str(errors))

		output = [line.replace('\n', '') for line in stdout.readlines()]
		return { "system" : output[0], "release" : output[1] }

# ------------------ SSHConnector