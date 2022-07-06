from enum import Enum
from sre_constants import SRE_FLAG_DEBUG
import pyrc.event.event as pyevent

class OSTYPE(Enum):
	LINUX = 1
	MACOS = 2
	WINDOWS = 3
	UNKNOW = 4

# ------------------ Connector
class Connector:

	@property
	def ostype(self) -> OSTYPE:
		return self.__ostype

	@ostype.setter
	def ostype(self, type:OSTYPE):
		self.__ostype = type

	def __deduce_ostype(self) -> OSTYPE:
		system = self.system()
		if system == "Windows":
			return OSTYPE.WINDOWS
		elif "Linux" in system:
			return OSTYPE.LINUX
		elif system == "Darwin":
			return OSTYPE.MACOS
		else:
			return OSTYPE.UNKNOW

	def __init__(self) -> None:
		self.__ostype:OSTYPE = self.__deduce_ostype()

	# ------------------------
	#		Custom functions
	# ------------------------

	# ------------------------
	#		To Override
	# ------------------------

	def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event:pyevent.Event = None):
		"""
		Executes the given command on the connected system in a given directory
		Args:
			cmd (str): command to execute
			cwd (str, optional): current working directory. Defaults to "".
			environment (dict, optional): environment variables. Defaults to None.
			event (pyevent.Event, optional): event to plug the command to. Defaults to None.

		Returns:
			event outputs
		"""
		return NotImplemented

	def is_remote(self) -> bool:
		"""
		Tells wether or not this connector would execute action on a remote machine
		Returns:
			bool
		"""
		return NotImplemented

	def is_open(self) -> bool:
		"""
		Tells wether or not this connector is up and running
		Returns:
			bool
		"""
		return NotImplemented

	def is_unix(self) -> bool:
		"""
		Tells wether or not this connector would execute action on a unix or windows machine
		Returns:
			bool
		"""
		return self.__ostype == OSTYPE.LINUX or self.__ostype == OSTYPE.MACOS

	def platform(self) -> 'dict[str:str]':
		"""
		Get connected system informations
		Raises:
			RuntimeError
		Returns:
			[dict[str:str]]: A dict of remote system informations. Keys are 'system' and 'release'
		"""
		return NotImplemented

	def system(self) -> str:
		"""
		Get connected system informations
		Raises:
			RuntimeError
		"""
		return self.platform()["system"]

# ------------------ Connector
