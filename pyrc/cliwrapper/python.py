from pyrc.system import FileSystem
from pyrc.cliwrapper import CLIWrapper
from pyrc.event import Event, ErrorRaiseEvent, CommandPrettyPrintEvent

class Python(CLIWrapper):
	def __init__(self, pyexe:str, connector:FileSystem = None, workdir:str = "") -> None:
		super().__init__(connector, workdir)

		if not self.connector.isexe(pyexe):
			raise RuntimeError(f"Python exe {pyexe} is not a valid path.")

		self.exe = pyexe
		self.venv = None
		# Virtual env script path deduction
		if self.is_venv():
			self.venv = self.prefix()

	def __call__(self, cmd:str, event:Event = None):
		"""
		Calls the command 'cmd' with the python executable
		"""
		return CLIWrapper.__call__(self, f"{self._source_cmd()} {self.exe} {cmd}", event)

	def _source_cmd(self) -> str:
		if self.venv is None: return ""
		# Virtual env script path deduction
		if self.connector.is_unix():
			source_cmd = self.connector.join(self.venv, "bin", "activate")
		else:
			source_cmd = self.connector.join(self.venv, "Scripts", "activate")
		return f"source {source_cmd} &&"

	def with_venv(self, cmd:str, event:Event = None):
		"""
		Invoque a system command but with the python virtual env sourced first.
		Note : This do NOT call python.
		"""
		return CLIWrapper.__call__(self, f"{self._source_cmd()} {cmd}", event)

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