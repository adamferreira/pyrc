
import os

try:
    import paramiko
    from scp import SCPClient, SCPException
    from pyrc.remote import SSHConnector
    _CMDEXEC_REMOTE_ENABLED_ = True
except:
    _CMDEXEC_REMOTE_ENABLED_ = False

try:
    from subprocess import *
    from subprocess import check_output
    _CMDEXEC_SUBPROCESS_ENABLED_ = True
except:
    _CMDEXEC_SUBPROCESS_ENABLED_ = False


class CommandExecutor:
    #def __init__(self):

    def __exec_local_cmd(self, cmd:str, flags:'list[str]' = [], print_output:bool = False, print_input:bool = True) -> 'list[str]':
        _cmd:'list[str]' = flags.copy()
        _cmd.insert(0, cmd)
        if _CMDEXEC_SUBPROCESS_ENABLED_:
            if print_input:
                print("[local]", " ".join(_cmd))

            try:
                out = str(check_output(_cmd).decode("utf-8")).split("\n")[:-1]
            except:
                print("Command", " ".join(_cmd), "cannot be launched.")
                return []

            if print_output:
                print(out)
            return out
        else:
            raise RuntimeError("Could not load subprocess module.")

    def __exec_remote_cmd(self, cmd:str, flags:'list[str]' = [], remote:SSHConnector = None , print_output:bool = False, print_input:bool = True) -> 'list[str]':
        _cmd:'list[str]' = flags.copy()
        _cmd.insert(0, cmd)
        if _CMDEXEC_REMOTE_ENABLED_:
            stdin, stdout, stderr = remote.exec_command(cmd, print_output, print_input)
            errors = stderr.readlines()
            if len(errors) > 0:
                raise RuntimeError(str(errors))

            return [line.replace("\n", "") for line in stdout.readlines()]
        else:
            raise RuntimeError("Could not load remote modules (paramiko, etc...).")

    def exec_command(self, cmd:str, flags:'list[str]' = [], remote:SSHConnector = None, print_output:bool = False, print_input:bool = True) -> 'list[str]':
        if remote is not None:
            try:
                return self.__exec_remote_cmd(cmd, flags, remote, print_output, print_input)
            except:
                raise RuntimeError("Could not connect to remote host.")
        else:
            return self.__exec_local_cmd(cmd, flags, print_output, print_input)