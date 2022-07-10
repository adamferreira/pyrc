
from pyrc.system import FileSystem, FileSystemCommand, OSTYPE
from pyrc.event import CommandPrettyPrintEvent

try:
    import docker
    __DOCKER_AVAILABLE__ = True
except:
    __DOCKER_AVAILABLE__ = False

class DockerEngine(FileSystemCommand):
	"""
	DockerEngine is will submit evey generated command (FileSystemCommand)
	to a docker client
	"""
	def __init__(self, image = None, container = None) -> None:
		FileSystemCommand.__init__(self)
		# Only works with linux style commands for now
		self.ostype = OSTYPE.LINUX
		self.image = image
		self.container = container

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event = None):
		assert self.container is not None

		if event is None:
			event = CommandPrettyPrintEvent(
				self, 
				print_input=True, 
				print_errors=True, 
				use_rich=True
			)

		exit_code, outputs = self.container.exec_run(
			cmd = f"bash -c \"{cmd}\"",
			workdir = cwd,
			environment = environment,
			stdout = True, stderr = True, stdin = False,
			demux = False, # Return stdout and stderr separately,
			stream = True
		)
		srdoutflux = outputs # Output is a Generator type (isinstance(outputs, Generator) == 1)
		event.begin(cmd, cwd, stdin = None, stderr = None, stdout = srdoutflux)
		return event.end() 

	#@overrides Necessary for FileSystem.__init__(self) as we overrides ostype
	def platform(self) -> 'dict[str:str]':
		return {
			"system" : FileSystem.os_to_str(FileSystem.ostype),
			"platform" : "unknown"
		}

	#@overrides
	def ls(self, path:str)-> 'list[str]':
		out = super().ls(path)
		return out[0].split("\n")