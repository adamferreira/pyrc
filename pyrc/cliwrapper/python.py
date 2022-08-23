from pyrc.system import FileSystem
from pyrc.cliwrapper import CLIWrapper
from pyrc.event import Event, ErrorRaiseEvent, CommandPrettyPrintEvent

class Python(CLIWrapper):
	def __init__(self, pyexe:str, connector:FileSystem = None) -> None:
		super().__init__(connector)

		if not self.connector.isexe(pyexe):
			raise RuntimeError(f"Python exe {pyexe} is not a valid path.")

		self.exe = pyexe
		self.venv = None
		# Virtual env script path deduction
		if self.is_venv():
			venv_prefix = self.prefix()
			if self.connector.is_unix():
				self.venv = self.connector.join(venv_prefix, "bin", "activate")
			else:
				self.venv = self.connector.join(venv_prefix, "Scripts", "activate")

	def __call__(self, cmd:str, cwd:str="", event:Event = None):
		"""
		Calls the command 'cmd' with the python executable
		"""
		source_cmd = f"source {self.venv} &&" if self.venv is not None else ""
		return CLIWrapper.__call__(self, f"{source_cmd} {self.exe} {cmd}", cwd, event)

	def with_venv(self, cmd:str, cwd:str="", event:Event = None):
		"""
		Invoque a system command but with the python virtual env sourced first.
		Note : This do NOT call python.
		"""
		source_cmd = f"source {self.venv} &&" if self.venv is not None else ""
		return CLIWrapper.__call__(self, f"{source_cmd} {cmd}", cwd, event)

	def base_prefix(self) -> str:
		"""
		Get the true path of the python exe
		"""
		base_prefix_cmd = """getattr(sys, 'base_prefix', None) or getattr(sys, 'real_prefix', None) or sys.prefix"""
		out, err, status = self(
			cmd = f"-c \"import sys; print({base_prefix_cmd})\"",
			event = ErrorRaiseEvent(self.connector) 
		)
		return out[0]

	def prefix(self) -> str:
		out, err, status = self(
			cmd = f"-c \"import sys; print(sys.prefix)\"",
			event = ErrorRaiseEvent(self.connector)
		)
		return out[0]

	def is_venv(self) -> bool:
		# https://stackoverflow.com/questions/1871549/determine-if-python-is-running-inside-virtualenv
		# Check if the python exe belong to a virtual env
		return self.base_prefix() != self.prefix()