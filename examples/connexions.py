import pyrc.remote as pyrm
import os, platform

if __name__ == '__main__':
    ssh_config_file = ""
    if platform.system() == "Linux":
        if "WSL2" in platform.release():
            ssh_config_file = os.path.join("/mnt" , "c", "Users", os.environ["USER"], ".ssh", "config")
        else:
            ssh_config_file = os.path.join("/home", os.environ["USER"], ".ssh", "config")

    if platform.system() == "Windows":
        ssh_config_file = os.path.join("C:", "Users", os.environ["USER"], ".ssh", "config")

    configs = pyrm.SSHConnector.get_ssh_configurations(ssh_config_file)
    for host in configs:
        print("Host", host, "config ->", configs[host])
