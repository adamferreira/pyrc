import os
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

class FileTransferTask():

    @property
    def taskid(self)->TaskID:
        return self.__taskid

    @property
    def filename(self)->str:
        return self.__file

    @property
    def name(self)->str:
        return os.path.basename(self.__file)

    @property
    def status(self)->TaskStatus:
        return self.__status

    def __init__(self, owner, file:str, user:str, hostname:str, endcb = None):
        self.__owner = owner
        self.__file = file
        self.__taskid = self.__owner.add_task(
            description = "[red]Downloading...", 
            filename=self.name, start=False, user=user, hostname=hostname)
        self.__owner.update(self.__taskid, total=os.path.getsize(file))
        self.__end_callback = endcb
        self.__status:TaskStatus = TaskStatus.SLEEPING
        

    def start(self):
        self.__owner.start_task(self.__taskid)
        self.__status = TaskStatus.STARTED

    def stop(self):
        self.__owner.stop_task(self.__taskid)
        if self.__status != TaskStatus.FINISHED:
            self.__status = TaskStatus.STOPPED

    def end(self):
        if self.__end_callback is not None:
            self.__end_callback(self)
        self.__status = TaskStatus.FINISHED

    def file_progress(self, filename:str, size:float, sent:float):
        self.__owner.update(self.__taskid, completed=sent)
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
                    TextColumn("[bold green]{task.fields[user]}@{task.fields[hostname]}"))

    def __init__(self, file, user:str, hostname:str, filetransferedcb = None, endcb = None):
        self.__richfileprogress = RemoteFileTransfer.getLayout()

        self.__tasks = {}
        self.__user = user
        self.__hostname = hostname
        self.__filetransferedcb = filetransferedcb
        self.__endcb = endcb

        if file is not None:
            if type(file) == str:
                self.add_file(file)
            if type(file) == list:
                [self.add_file(file) for file in file]

    def add_file(self, file:str):
        task = FileTransferTask(self.__richfileprogress, file, self.__user, self.__hostname, endcb = self.__filetransferedcb)
        self.__tasks[task.name] = task

    def start(self):
        self.__richfileprogress.start()
        [t.start() for t in self.__tasks.values()]

    def stop(self):
        [t.stop() for t in self.__tasks.values()]
        self.__richfileprogress.stop()

    def file_progress(self, filename:str, size:float, sent:float):
        self.__tasks[filename.decode("utf-8")].file_progress(filename, size, sent)

    def end(self):
        if self.__endcb is not None:
            self.__endcb(self)

    def tasks(self) -> 'List[FileTransferTask]':
        return self.__tasks.values()


class DirectoryTransferProgress():
    def __init__(self, dir:str, files:'List[str]', user:str, hostname:str):
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
    
