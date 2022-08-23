from pyrc.system import FileSystem, LocalFileSystem

class CLIWrapper(object):
	connector:FileSystem

	def __init__(self, connector:FileSystem = None) -> None:
		# Default connector is local
		if connector is None:
			self.connector = LocalFileSystem()
		else:
			self.connector = connector