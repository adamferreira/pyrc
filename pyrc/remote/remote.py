import os, paramiko, platform
from pyrc.remote import SSHConnector

def get_ssh_configurations(user_config_file:str) -> 'dict[str:dict[str:str]]':
    ssh_config = paramiko.SSHConfig.from_path(user_config_file)
    return {hostname : ssh_config.lookup(hostname) for hostname in ssh_config.get_hostnames()}


def create_connectors(user_config_file:str, sshkey:str=None) -> 'dict[str:SSHConnector]':
    # Exception if file does not exist
    ssh_configs = get_ssh_configurations(user_config_file)

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
            user=user_config["user"],
            hostname=user_config["hostname"],
            sshkey=sshkey,
            port = user_config["port"] if "port" in user_config else 22,
            proxycommand=user_config["proxycommand"] if "proxycommand" in user_config else None,
            askpwd = False
        )
    return connectors

def create_default_connectors()  -> 'dict[str:SSHConnector]':
    ssh_config_file = ""
    if platform.system() == "Linux":
        if "WSL2" in platform.release():
            ssh_config_file = os.path.join("/mnt" , "c", "Users", os.environ["USER"], ".ssh", "config")
        else:
            ssh_config_file = os.path.join("/home", os.environ["USER"], ".ssh", "config")

    if platform.system() == "Windows":
        ssh_config_file = os.path.join("C:\\", "Users", os.environ["USER"], ".ssh", "config")

    return create_connectors(ssh_config_file, sshkey=None)

class RemotePyrc(object):
	def __init__(self, remote:SSHConnector, python_remote_install:str = None):
		assert remote.is_opent()
		self.__githuburl = "https://github.com/adamferreira/pyrc.git"

    #def get_python_version(self):
    #    return major, minor, patch
