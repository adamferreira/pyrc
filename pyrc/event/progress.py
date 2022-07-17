from enum import Enum
from rich import print
from rich.progress import (
	BarColumn,
	DownloadColumn,
	Progress,
	TaskID,
	TextColumn,
	TimeRemainingColumn,
	TransferSpeedColumn,
	SpinnerColumn,
)

class TaskStatus(Enum):
	SLEEPING = 1
	STARTED = 2
	STOPPED = 3
	FINISHED = 4 


# TODO : make it an event ?
class FileTransferTask():
	@property
	def taskid(self) -> TaskID:
		return self.__taskid

	@property
	def filename(self) -> str:
		return self.__file

	@property
	def name(self) -> str:
		return self.__from_fs.basename(self.__file)

	@property
	def status(self) -> TaskStatus:
		return self.__status

	def prettyname(self) -> str:
		if type(self.__to_fs).__name__ ==  'RemoteSSHFileSystem':
			return f"{self.__to_fs.user}@{self.__to_fs.hostname}"
		else:
			return str(type(self.__to_fs).__name__)

	def __init__(self,
			layout,
			file:str,
			from_fs:'FileSystem',
			to_fs:'FileSystem'
		):
		self.__layout = layout
		self.__file = file
		self.__from_fs = from_fs
		self.__to_fs = to_fs

		self.__taskid = self.__layout.add_task(
			description = "[red]Downloading...", 
			filename = self.__from_fs.basename(self.__file), 
			start = False, 
			prettyname = self.prettyname()
		)
		# Get file name from system that send the file
		self.__layout.update(self.__taskid, total = self.__from_fs.getsize(file))
		self.__status:TaskStatus = TaskStatus.SLEEPING
		

	def start(self):
		self.__layout.start_task(self.__taskid)
		self.__status = TaskStatus.STARTED

	def stop(self):
		self.__layout.stop_task(self.__taskid)
		if self.__status != TaskStatus.FINISHED:
			self.__status = TaskStatus.STOPPED

	def end(self):
		"""
		if self.__end_callback is not None:
			self.__end_callback(self)
		self.__status = TaskStatus.FINISHED
		"""

	# Paramiko's scp like callback
	def file_progress(self, filename:str, size:float, sent:float):
		self.__layout.update(self.__taskid, completed=sent)
		if sent == size:
			self.end()

class RemoteFileTransfer():

	@staticmethod
	def getLayout():
		return Progress(
					SpinnerColumn(),
					TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
					BarColumn(bar_width=None),
					"[progress.percentage]{task.percentage:>3.1f}%",
					"•",
					DownloadColumn(),
					"•",
					TransferSpeedColumn(),
					"•",
					TimeRemainingColumn(),
					"•",
					TextColumn("[bold green]{task.fields[prettyname]}"))

	def __init__(self, files:'list[str]', from_fs:'FileSystem', to_fs:'FileSystem'):
		self.__richfileprogress = RemoteFileTransfer.getLayout()

		self.__tasks = {}
		self.__from_fs = from_fs
		self.__to_fs = to_fs

		if files is not None:
			if type(files) == str:
				self.add_file(files)
			if type(files) == list:
				[self.add_file(file) for file in files]

	def add_file(self, file:str):
		task = FileTransferTask(
			layout = self.__richfileprogress,
			file = file,
			from_fs = self.__from_fs,
			to_fs = self.__to_fs
		)
		self.__tasks[task.name] = task

	def tasks(self) -> 'list[FileTransferTask]':
		return self.__tasks.values()

	def start(self):
		self.__richfileprogress.start()
		[t.start() for t in self.__tasks.values()]

	def stop(self):
		[t.stop() for t in self.__tasks.values()]
		self.__richfileprogress.stop()

	# Paramiko's scp like callback
	def file_progress(self, filename:str, size:float, sent:float):
		self.__tasks[filename.decode("utf-8")].file_progress(filename, size, sent)

# TODO rework
class DirectoryTransferProgress():
	def __init__(self, dir:str, files:'list[str]', user:str, hostname:str):
		self.__overallprogress = Progress(
			SpinnerColumn(),
			TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
			BarColumn(),
			"[progress.percentage]{task.percentage:>3.1f}%",
			"•",
			TextColumn("[bold green]{task.fields[user]}@{task.fields[hostname]}"))

		self.__filesprogress = RemoteFileTransfer(files, self.caller.user, self.caller.hostname, filetransferedcb=self.__file_transfered)

	def __file_transfered(self):
		return None

	def file_progress(self, filename:str, size:float, sent:float):
		return self.__filesprogress.file_progress_callback(filename, size, sent)
	
