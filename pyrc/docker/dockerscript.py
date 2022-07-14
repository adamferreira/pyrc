from typing import Union, List
from pyrc.event import CommandPrettyPrintEvent
from pyrc.system import ScriptGenerator, OSTYPE

class DockerFile(ScriptGenerator):
	"""
	DockerFile is a ScriptGenerator that store dockerfile-like commands in a dockerfile
	"""
	def __init__(self, dockerfile:str, silent:bool = False) -> None:
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
						environment = None,
						event = self.default_event()
					)
		else:
			event.begin(cmd, cwd, stdin = None, stderr = None, stdout = None)
			event.end()

		self.script.writelines([
			f"{cmd}\n"
		])

	def append_dockerfile(self, dockerfile:str) -> "DockerFile":
		with open(dockerfile, 'r') as d:
			for line in d.readlines():
				line = line.strip("\n")
				self.exec_command(line)


	def FROM(self, image:str) -> "DockerFile":
		self.exec_command(f"{self.FROM.__name__} {image}")
		return self

	def RUN(self, statements:Union[str, List[str]]) -> "DockerFile":
		if isinstance(statements, str):
			return self.RUN([statements])

		if len(statements) == 0: return self

		if len(statements) == 1:
			self.exec_command(f"{self.RUN.__name__} {statements[0]}")
		else:
			run = "; \ \n\t".join(statements)
			self.exec_command(f"{self.RUN.__name__} {run}")

		return self

	def USER(self, user:str) -> "DockerFile":
		self.exec_command(f"{self.USER.__name__} {user}")
		return self

	def ENTRYPOINT(self, user:str) -> "DockerFile":
		self.exec_command(f"{self.ENTRYPOINT.__name__} {user}")
		return self

	def ENV(self, var:str, value:str) -> "DockerFile":
		self.exec_command(f"{self.ENV.__name__} {var} {value}")
		return self

	def CMD(self, cmd:str) -> "DockerFile":
		self.exec_command(f"{self.CMD.__name__} [\"{cmd}\"]")
		return self