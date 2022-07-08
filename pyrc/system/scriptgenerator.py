import pyrc.system as pysys
from pyrc.system.command import FileSystemCommand

class ScriptGenerator(FileSystemCommand):
	"""
	ScriptGenerator is will submit evey generated command (FileSystemCommand)
	to a file by overriding exec_command
	"""
	def __init__(self, 
			script_path:str, 
			ostype:pysys.OSTYPE = pysys.OSTYPE.LINUX
		):
		# Set up type
		self.ostype = ostype

		# Seyup script file
		assert self.isdir(self.dirname(script_path))
		self.script = open(script_path, "w+")
		self.__last_printed_env:str = ""

	def __del__(self):
		if self.script is not None:
			self.script.close()

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
		# stdout = ["ok"], stderr = []
		return ["ok"], []