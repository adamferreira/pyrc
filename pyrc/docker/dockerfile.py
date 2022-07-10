from ctypes import Union
from typing import List
from pyrc.event import CommandPrettyPrintEvent
from pyrc.system import ScriptGenerator, OSTYPE

class DockerFile(ScriptGenerator):
	"""
	DockerFile is a ScriptGenerator that store dockerfile-like commands in a dockerfile
	"""
	def __init__(self, dockerfile:str, silent = True) -> None:
		ScriptGenerator.__init__(
			self,
			script_path = dockerfile,
			ostype = OSTYPE.LINUX
		)
		self.silent = silent

	def default_event(self):
		return CommandPrettyPrintEvent(
				self, 
				print_input=True, 
				print_errors=True, 
				use_rich=True
			)

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event = None):
		if event is None and not self.silent:
			return self.exec_command(
						cmd = cmd, 
						cwd = cwd,
						environment = environment,
						event = self.default_event()
					)
		else:
			event.begin(cmd, cwd, stdin = None, stderr = None, stdout = None)
			event.end()

		self.script.writelines([
			f"{cmd}\n",
			"\n"
		])

	def FROM(self, image:str) -> "DockerFile":
		self.exec_command(f"{self.FROM.__name__} {image}")
		return self

	def RUN(self, statements:Union[str, List[str]]) -> "DockerFile":
		if isinstance(statements, str):
			return self.RUN([statements])

		[self.exec_command(f"{self.RUN.__name__} {s}") for s in statements]
		return self

	def USER(self, user:str) -> "DockerFile":
		self.exec_command(f"{self.USER.__name__} {user}")
		return self