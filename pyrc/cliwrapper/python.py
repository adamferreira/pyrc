from pyrc.system import FileSystem
from pyrc.cliwrapper import CLIWrapper
from pyrc.event import Event, ErrorRaiseEvent, CommandPrettyPrintEvent

class Python(CLIWrapper):
	@property
	def modules(self) -> CLIWrapper:
		"""
		Returns a new CLIWrapper encapsulating the '-m' argument
		"""
		return self.arg("-m")

	def __init__(self, pyexe:str, connector:FileSystem = None, workdir:str = "") -> None:
		super().__init__(pyexe, connector, workdir)

		if not self.connector.isexe(pyexe):
			raise RuntimeError(f"Python exe {pyexe} is not a valid path.")

		self.venv = None
		# Virtual env script path deduction
		if self.is_venv():
			self.venv = self.system_prefix()

	def _source_cmd(self) -> str:
		if self.venv is None: return ""
		# Virtual env script path deduction
		if self.connector.is_unix():
			source_cmd = self.connector.join(self.venv, "bin", "activate")
		else:
			source_cmd = self.connector.join(self.venv, "Scripts", "activate")
		return f"source {source_cmd} &&"

	def arg(self, arg:str) -> 'CLIWrapper':
		return CLIWrapper(
			prefix = f"{self._source_cmd()} {self.prefix} {arg}",
			connector = self.connector,
			workdir = self.workdir
		)

	def __call__(self, cmd:str, event:Event = None):
		"""
		Calls the command 'cmd' with the python executable
		"""
		return CLIWrapper(
			prefix = f"{self._source_cmd()} {self.prefix}",
			connector = self.connector,
			workdir = self.workdir
		).__call__(cmd, event)

	def inline(self, cmd:str) -> CLIWrapper:
		"""
		Invoque the given command 'cmd' as an inline python command
		It calls <python> -c \"cmd\"
		"""
		return self.arg("-c").arg(f"\"{cmd}\"")

	def with_venv(self, cmd:str, event:Event = None):
		"""
		Invoque a system command but with the python virtual env sourced first.
		Note : This do NOT call python.
		"""
		return CLIWrapper(
			prefix = self._source_cmd(),
			connector = self.connector,
			workdir = self.workdir
		).__call__(cmd, event)

	def system_base_prefix(self) -> str:
		"""
		Get the true path of the python exe
		"""
		base_prefix_cmd = """getattr(sys, 'base_prefix', None) or getattr(sys, 'real_prefix', None) or sys.prefix"""
		out, err, status = self(
			cmd = f"-c \"import sys; print({base_prefix_cmd})\"",
			event = ErrorRaiseEvent(self.connector) 
		)
		return out[0]

	def system_prefix(self) -> str:
		"""
		Get the value of sys.prefix of this python executable
		"""
		# self.inline("import sys; print(sys.prefix)")(event = ErrorRaiseEvent(self.connector))
		out, err, status = self(
			cmd = f"-c \"import sys; print(sys.prefix)\"",
			event = ErrorRaiseEvent(self.connector)
		)
		return out[0]

	def is_venv(self) -> bool:
		# https://stackoverflow.com/questions/1871549/determine-if-python-is-running-inside-virtualenv
		# Check if the python exe belong to a virtual env
		return self.system_base_prefix() != self.system_prefix()

	def version(self) -> str:
		out, err, status = self("--version")
		return out[0].replace("Python ", "")

if __name__ == "__main__":
	#Python("/usr/bin/python3")("--version")
	#print(type(Python("/usr/bin/python3").arg("--version")))
	#Python("/usr/bin/python3").arg("--version")("")