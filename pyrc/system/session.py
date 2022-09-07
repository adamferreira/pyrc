from pyrc.system.filesystem import FileSystem
from pyrc.event import Event

class Session:
	connector:FileSystem
	workingdir:str
	"""
	Session holds a FileSystem object as a connector to submit commands to
	Session also stores an environment variables dict to pass down to the connector
	Session also stores the current working directory to pass down to the connector (FileSystem object)
	"""
	# dict[str,str]
	class EnvironDict(dict):
		"""
		EnvironDict acts as a gateway to a FileSystem object to get and set env variable of this FileSystem
		d[var] invoques d.filesystem.env(key)
		d[var] = value stores the values in the dict and will be passed down to the FileSystem in the next exec_command call
		"""
		def __init__(self, path:FileSystem):
			super().__init__()
			self.__path = path

		def __getitem__(self, key:str) -> str:
			if key in self:
				return super().__getitem__(key)
			else:
				self.__setitem__(key, self.__path.env(key))
				return super().__getitem__(key)

		def __setitem__(self, key, value):
			return super().__setitem__(key, value)

	def __init__(self, connector:FileSystem, workingdir:str = "") -> None:
		# FileSystem connection
		self.connector = connector
		# Working directory to run the commands in
		self.workingdir = workingdir
		# Environment variables
		self.environ = Session.EnvironDict(self.connector)

	def exec_command(self, cmd:str, event:Event):
		return self.connector.exec_command(
			cmd = cmd,
			cwd = self.workingdir,
			environment = self.environ,
			event = event
		)