
from typing import Union, List
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
	def __init__(self, user:str, image = None, container = None) -> None:
		FileSystemCommand.__init__(self)
		# Only works with linux style commands for now
		self.ostype = OSTYPE.LINUX
		self.user = user
		self.image = image
		self.container = container

	#@overrides
	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event = None):
		assert self.container is not None
		environment = {} if environment is None else dict(environment)
		environment.update(self.environ)

		# to avoid "OCI runtime exec failed: exec failed: Cwd must be an absolute path: unknown"
		# check if cwd is empty ot avoid recursive call
		workdir = cwd if cwd == "" else self.evaluate_path(cwd)

		exit_code, outputs = self.container.exec_run(
			cmd = f"bash -c \"{cmd}\"",
			# to avoid "OCI runtime exec failed: exec failed: Cwd must be an absolute path: unknown"
			workdir = workdir,
			environment = environment,
			user = self.user,
			stdout = True, stderr = True, stdin = False,
			demux = False, # Return stdout and stderr separately,
			stream = True
		)

		if event is not None:
			srdoutflux = outputs # Output is a Generator type (isinstance(outputs, Generator) == 1)
			event.begin(cmd, workdir, stdin = None, stderr = None, stdout = srdoutflux)
			return event.end()

		return [], [], []

	def bash(self, cmds:Union[str, List[str]], cwd:str = "", silent:bool = False, environment:dict = None):
		if isinstance(cmds, str):
			return self.bash([cmds], cwd, environment)

		event = None
		if not silent:
			event = CommandPrettyPrintEvent(
				self, 
				print_input=True, 
				print_errors=True, 
				use_rich=True
			)

		outputs = []
		for cmd in cmds:
			out, err, status = self.exec_command(cmd, cwd, environment, event)
			outputs.extend(out)
		return outputs

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

	def append_bashrc(self, line:str) -> None:
		"""
		Append the given line to the end of ~/.bashrc
		"""
		self.evaluate(f"echo \"{line}\" >> ~/.bashrc")

	def register_env(self, var:str, value:str) -> None:
		"""
		Add export <var>=<value> to the user bashrc file
		"""
		self.append_bashrc("export" + "\ " + var + "=" + value)
		# Also set the variable for the current sessiobn
		self.environ[var] = value