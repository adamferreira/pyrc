from pyrc.system import FileSystem, LocalFileSystem
from pyrc.event import Event, ErrorRaiseEvent, CommandPrettyPrintEvent

# CLI Wrappers are callable objects
class CLIWrapper(object):
	connector:FileSystem

	def __init__(self, connector:FileSystem = None) -> None:
		# Default connector is local
		if connector is None:
			self.connector = LocalFileSystem()
		else:
			self.connector = connector

		# Plug python environ to its connector
		self.environ = self.connector.environ

	def __call__(self, cmd:str, cwd:str="", event:Event = None):
		return self.connector.exec_command(
			cmd = cmd,
			cwd = cwd,
			environment = self.environ,
			event = self.default_event() if event is None else event
		)

	def default_event(self) -> Event:
		#return ErrorRaiseEvent(self.connector)
		return CommandPrettyPrintEvent(
			self.connector,
			print_input = True,
			print_errors = True,
			use_rich = True
		)