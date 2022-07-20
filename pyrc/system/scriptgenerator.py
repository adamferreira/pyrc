import pyrc.system as pysys
from pyrc.system import FileSystemCommand
from pyrc.system import FileSystem

class ScriptGenerator(FileSystemCommand):

	@property
	def filename(self) -> str:
		return self.script.name

	"""
	ScriptGenerator is will submit evey generated command (FileSystemCommand)
	to a file by overriding exec_command
	"""
	def __init__(self, 
			script_path:str, 
			ostype:pysys.OSTYPE = pysys.OSTYPE.LINUX
		) -> None:

		FileSystemCommand.__init__(self)

		# Set up type
		self.ostype = ostype

		# Setup script file
		assert pysys.LocalFileSystem().isdir(pysys.LocalFileSystem().dirname(script_path))
		self.script = open(script_path, "w+")
		self.__last_printed_env:str = ""

	def __del__(self):
		self.close()
		
	def close(self):
		if self.script is not None and not self.script.closed:
			self.script.close()

	#@overrides
	def name(self) -> str:
		return self.script.name if self.script is not None else ""

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event = None):
		if environment is not None:
			# Do not reprint envs var is its the same than last call
			# Because PATH=<vars>:PATH would became VERY long if called to many times
			if self.__last_printed_env != str(environment):
				self.script.writelines([f"export {var}={val}\n" for var,val in environment.items()])
				self.script.writelines(["\n"])
				self.__last_printed_env = str(environment)

		self.script.writelines([
			f"cd {cwd}\n",
			f"{cmd}\n",
			"\n"
		])

		# Trick so that 'isdir', 'isfile', etc always returns 'True'
		# Because the connection is fake and pyrc-using python scripts would like to use those check
		# when using genuine remote connector
		# stdout = ["ok"], stderr = [], status = 0
		return ["ok"], [], 0

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