from pyrc.system import FileSystem, LocalFileSystem
from pyrc.event import Event, ErrorRaiseEvent, CommandPrettyPrintEvent

# CLI Wrappers are callable objects
class CLIWrapper(object):
	connector:FileSystem

	def __init__(self, prefix:str, connector:FileSystem = None, workdir:str = "") -> None:
		# Default connector is local
		if connector is None:
			self.connector = LocalFileSystem()
		else:
			self.connector = connector

		self.prefix = prefix
		self.workdir = workdir
		# Plug environ to its connector's
		self.environ = self.connector.environ

	# Overriding
	# This will be called for every arg self.arg that is not yet registered in the class
	# CLIWrapper("git").arg("checkout") is equivalent to CLIWrapper("git").checkout
	def __getattr__(self, name):
		# Do NOT register the new attribute
		return self.arg(name)

	def __call__(self, cmd:str, event:Event = None):
		return self.connector.exec_command(
			cmd = f"{self.prefix} {cmd}",
			cwd = self.workdir,
			environment = self.environ,
			event = self.default_event() if event is None else event
		)

	def arg(self, arg:str) -> 'CLIWrapper':
		"""
		Returns a new CLIWrapper with {arg} appended to self's prefix
		CLIWrapper("foo") has the prefix "foo"
		CLIWrapper("foo").arg("bar") has the prefix "foo bar"
		Equivalently, CLIWrapper("foo").bar has the prefix "foo bar"
		"""
		return type(self)(
			prefix = f"{self.prefix} {arg}",
			connector = self.connector,
			workdir = self.workdir
		)

	def default_event(self) -> Event:
		#return ErrorRaiseEvent(self.connector)
		return CommandPrettyPrintEvent(
			self.connector,
			print_input = True,
			print_errors = True,
			use_rich = True
		)

if __name__ == "__main__":
	# CLIWrapper("git").arg("checkout").arg("-b")("my_branch") is equivalent to CLIWrapper("git")("checkout -b my_branch")
	assert CLIWrapper("git").arg("checkout").arg("-b").arg("my_branch").prefix == "git checkout -b my_branch"
	assert CLIWrapper("git").checkout.arg("-b").my_branch.prefix == "git checkout -b my_branch"