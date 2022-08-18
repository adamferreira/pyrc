import paramiko
from pyrc.system import LocalFileSystem
from pyrc.remote import RemoteSSHFileSystem

def get_default_keys_paths() -> 'tuple(str,str)':
	path = LocalFileSystem()
	platform = path.platform()
	if path.is_unix():
		if "WSL2" in platform["release"]:
			ssh_dir = path.join("/mnt" , "c", "Users", path.env("USER"), ".ssh")
		else:
			ssh_dir = path.join("/home", path.env("USER"), ".ssh")
	else:
		ssh_dir = path.join("C:\\", "Users", path.env("USER"), ".ssh")

	return path.join(ssh_dir, "id_rsa"), path.join(ssh_dir, "id_rsa.pub")

def get_default_ssh_config() -> 'dict[str:dict[str:str]]':
	path = LocalFileSystem()
	platform = path.platform()
	if path.is_unix():
		if "WSL2" in platform["release"]:
			ssh_config_file = path.join("/mnt" , "c", "Users", path.env("USER"), ".ssh", "config")
		else:
			ssh_config_file = path.join("/home", path.env("USER"), ".ssh", "config")
	else:
		ssh_config_file = path.join("C:\\", "Users", path.env("USER"), ".ssh", "config")

	return get_ssh_configurations(ssh_config_file)

def get_ssh_configurations(user_config_file:str) -> 'dict[str:dict[str:str]]':
	ssh_config = paramiko.SSHConfig.from_path(user_config_file)
	return {hostname : ssh_config.lookup(hostname) for hostname in ssh_config.get_hostnames()}

def create_sshconnectors(ssh_configs:dict, sshkey:str=None) -> 'dict[str:RemoteSSHFileSystem]':
	path = LocalFileSystem()

	# If no sshkey specified we add one from the folder where the config file is
	if sshkey is None:
		ssh_priv, ssh_pub = get_default_keys_paths()
		sshkey = ssh_priv
	
	connectors = {}
	for hostname in ssh_configs:
		if hostname == "*":
			continue
		
		# Creating user config dictionnary
		user_config = ssh_configs[hostname]
		sshfilesystem_args = {
			"username": user_config["user"],
			"hostname" : user_config["hostname"],
			"key_filename" : sshkey,
			"port" : user_config["port"] if "port" in user_config else 22,
			"askpwd" : False
		}
		if "proxycommand" in user_config:
			sshfilesystem_args["proxycommand"] = user_config["proxycommand"]

		connectors[hostname] = RemoteSSHFileSystem(**sshfilesystem_args)
	return connectors

def create_default_sshconnectors()  -> 'dict[str:RemoteSSHFileSystem]':
	return create_sshconnectors(get_default_ssh_config(), sshkey=None)

class RemotePyrc(object):
	def __init__(self, remote:RemoteSSHFileSystem, python_remote_install:str = None):
		assert remote.is_opent()
		self.__githuburl = "https://github.com/adamferreira/pyrc.git"
