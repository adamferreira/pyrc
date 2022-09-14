import io
from typing import List, Dict
from pyrc.system.command import FileSystemCommand
from pyrc.system.filesystem import FileSystem, OSTYPE
from pyrc.system.local import LocalFileSystem

class ScriptGenerator(FileSystemCommand):

	@property
	def filename(self) -> str:
		return self.file.name

	"""
	ScriptGenerator is will submit evey generated command (FileSystemCommand)
	to a file by overriding exec_command
	"""
	def __init__(self, 
			script_path:str,
			mode:str,
			ostype:OSTYPE = OSTYPE.LINUX
		) -> None:

		FileSystemCommand.__init__(self)
		# Check, file should exists or belongs to an existing directory
		local = LocalFileSystem()
		assert local.isfile(script_path) or local.isdir(local.dirname(script_path))

		# Set up type ans mode
		self.mode = mode
		self.ostype = ostype
		self.file = None

	def __del__(self):
		self.close()
		
	def close(self):
		if self.file is not None and not self.file.closed:
			self.file.close()

	def open(self) -> 'ScriptGenerator':
		self.file = io.open(self.script_path, self.mode)
		return self

	#--------------------------
	# Context Manager pattern
	#--------------------------
	def __enter__(self):
		self.file = self.open()
		return self
	
	def __exit__(self):
		self.close()

	#@overrides
	def name(self) -> str:
		return self.file.name if self.file is not None else ""

	#--------------------------
	# File Writting
	#--------------------------

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event = None):
		"""
		For ScriptGenerator, all submitted command are writtend into a file eastead of being executed.
		If cmd is not "", a cd to 'cwd' is performed before calling 'cmd'
		'environment' and 'event' are ignored
		"""
		lines = [f"{cmd}\n"] if cwd == "" else [f"{cmd}\n", f"cd {cwd}\n"]
		self.file.writelines(lines)

		# Trick so that 'isdir', 'isfile', etc always returns 'True'
		# Because the connection is fake and pyrc-using python scripts would like to use those check
		# when using genuine remote connector
		# stdout = ["ok"], stderr = [], status = 0
		return ["ok"], [], 0

	def writeline(self, line:str) -> None:
		self.exec_command(
			cmd = line,
			cwd = "",
			environment = None,
			event = None
		)

	def writelines(self, lines:List[str]) -> None:
		[self.writeline(l) for l in lines]

	def export(self, variables:Dict[str, str]) -> None:
		"""
		Export the given variables in the script.
		Calls 'export k = v' for every k,v in variables
		"""
		self.writelines([f"export {var}={val}\n" for var,val in variables.items()])
		self.writeline("\n")

	def export_environ(self) -> None:
		"""
		Export this connector's 'environ' dict in the script as exports
		"""
		self.export(self.environ)

	#--------------------------
	# pyrc FileSystem Overloards
	#--------------------------

	#@overrides Necessary for FileSystem.__init__(self) as we overrides ostype
	def platform(self) -> 'dict[str:str]':
		return {
			"system" : FileSystem.os_to_str(FileSystem.ostype),
			"platform" : "unknown"
		}

	#@overrides
	def is_remote(self) -> bool:
		return False

	#@overrides
	def is_open(self) -> bool:
		return True

	#@overrides (useless fct)
	def env(self, var:str) -> str:
		return self.exec_command(f"${var}")


# Utilitary Class for Bash scripting on linux
class BashScriptGenerator(ScriptGenerator):
	def __init__(self, script_path: str) -> None:
		super().__init__(script_path, OSTYPE.LINUX)

	def ifelse(self, condition:str, ifstm:str, elsestm = None) -> None:
		self.writeline(f"if [[ {condition} ]]")
		self.writelines(["then", f"\t{ifstm}"])
		if elsestm is not None:
			self.writelines(["else", f"\t{elsestm}"])
		self.writeline("fi")
