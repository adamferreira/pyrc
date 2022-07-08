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
	def mkdir(self, path:str, mode=0o777, parents=False, exist_ok=False):
		event = pyevent.CommandStoreEvent()
		out, err = [], []
		if self.is_unix():
			flag = " -p " if parents or exist_ok else ""
			"""TODO make mode work on remote machine"""
			#flag = " ".join([flag, "-m " + str(mode)])
			out, err, status = self.exec_command(cmd = f"mkdir {flag} {path}", event = event)
		else: # No need for -p flag in Windows
			out, err, status = self.exec_command(cmd = f"mkdir {path}", event = event)

		if len(err) > 0:
			if "File exists" in "".join(err):
				raise FileExistsError('\n'.join(err))
			else:
				raise RuntimeError('\n'.join(err))

	#@overrides
	def rmdir(self, path:str, recur:bool = False):
		if self.is_unix():
			cmd_ = "rm -rf" if recur else "rmdir"
			out, err, status = self.exec_command(
				cmd = f"{cmd_} {path}",
				event = pyevent.ErrorRaiseEvent()
			)
		else:
			raise RuntimeError("rmdir is only available on unix remote systems.")

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

	#@overrides
	def ls(self, path:str)-> 'List[str]':
		if self.is_unix():
			out, err, status = self.exec_command(cmd = f"ls {path}", event=pyevent.ErrorRaiseEvent())
			return out
		else:
			out, err, status = self.exec_command(cmd = f"dir {path}", event=pyevent.ErrorRaiseEvent())
			return out

	#@overrides
	def lsdir(self, path:str):
		# Do nothing
		return None

	#@overrides
	def isfile(self, path:str) -> bool:
		if self.is_unix():
			out, err, status = self.exec_command(cmd = f"[[ -f {path} ]] && echo \"ok\"", event=pyevent.ErrorRaiseEvent())
			if len(out) == 0: return False
			else : return "ok" in out[0]
		else:
			# TODO
			raise RuntimeError("isfile not supported for Windows remote systems")

	#@overrides
	def isdir(self, path:str) -> bool:
		if self.is_unix():
			out, err, status = self.exec_command(cmd = f"[[ -s {path} ]] && echo \"ok\"", event=pyevent.ErrorRaiseEvent())
			if len(out) == 0: return False
			else : return "ok" in out[0]
		else:
			# TODO
			raise RuntimeError("isdir not supported for Windows remote systems")

	#@overrides
	def islink(self, path:str) -> bool:
		if self.is_unix():
			out, err, status = self.exec_command(cmd = f"[[ -L {path} ]] && echo \"ok\"", event=pyevent.ErrorRaiseEvent())
			if len(out) == 0: return False
			else : return "ok" in out[0]
		else:
			# TODO
			raise RuntimeError("islink not supported for Windows remote systems")

	#@overrides
	def touch(self, path:str):
		parent = self.dirname(path)
		if not self.isdir(parent):
			raise RuntimeError(f"Path {parent} is not a valid directory.")

		if self.is_unix():
			self.exec_command(f"touch {path}")
		else:
			self.exec_command(f"call > {path}")

	#@overrides
	def zip(self, path:str, archivename:str = None, flag:str = "") -> None:
		FileSystem.zip(self, path, archivename)
		if self.is_unix():
			return self.exec_command(f"zip {flag} \"{archivename}\" \"{path}\"")
		else:
			return NotImplemented

	#@overrides
	def env(self, var:str) -> str:
		return self.check_output(f"python -c \"import os; print(os.environ[\'{var}\'])\"")[0]

# ------------------ FileSystemCommad