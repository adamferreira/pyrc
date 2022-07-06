import os, platform
from pyrc.system.filesystem import FileSystem
import pyrc.event.event as pyevent

try:
    from subprocess import *
    from subprocess import check_output
    _CMDEXEC_SUBPROCESS_ENABLED_ = True
except:
    _CMDEXEC_SUBPROCESS_ENABLED_ = False

# ------------------ LocalFileSystem
class LocalFileSystem(FileSystem):
	def __init__(self) -> None:
		super().__init__()

	# ------------------------
	#		Overrides
	# ------------------------

	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		event = pyevent.CommandPrettyPrintEvent(self) if event is None else event
		p = Popen([f"cd {cwd};{cmd}"], stdin = PIPE, stdout = PIPE, stderr = PIPE, env = environment, shell = True)
		event.begin(cmd, cwd, p.stdin, p.stdout, p.stderr)
		#os.system(full_cmd) #TODO use os.system for realtime python stdout feed ?
		return event.end()

	def is_remote(self) -> bool:
		return False

	def platform(self) -> 'dict[str:str]':
		return {
			"system" : self.system(),
			"release" : "unknown"
		}

	def system(self) -> str:
		return platform.system()


# ------------------ LocalFileSystem