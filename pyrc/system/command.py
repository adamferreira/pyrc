from pyrc.system.filesystem import FileSystem
import pyrc.event.event as pyevent

# ------------------ FileSystemCommad
class FileSystemCommand(FileSystem):
	"""
	This class is used when system actions should be commands.
	For example, self.mkdir(...) will call self.exec_command("mkdir ...") on unix connectors.
	This is the exact opposite of LocalFileSystem which would call os.mkdir(...).
	"""
	def __init__(self) -> None:
		super().__init__()

	# ------------------------
	#		To Override
	# ------------------------
	
	#@overrides
	def unlink(self, path:str, missing_ok:bool=False) -> None:
		if not missing_ok and not (self.isfile(path) or self.islink(path)):
			raise FileNotFoundError(f"Remote file {path} does not exist.")
		if self.is_unix():

			out, err, status = self.exec_command(
				cmd = f"rm -f {path}",
				event = pyevent.ErrorRaiseEvent()
			)
		else:
			raise RuntimeError("unlink is only available on unix remote systems.")
# ------------------ FileSystemCommad