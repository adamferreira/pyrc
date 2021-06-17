import os

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

    def __init__(self, owner, file:str, user:str, hostname:str):
        self.__owner = owner
        self.__file = file
        self.__taskid = self.__owner.add_task(
            description = "[red]Downloading...", 
            filename=self.name, start=False, user=user, hostname=hostname)
        self.__owner.update(self.__taskid, total=os.path.getsize(file))
        self.__end_callback = None

    def start(self):
        self.__owner.start_task(self.__taskid)

    def stop(self):
        self.__owner.stop_task(self.__taskid)

    def end(self):
        if self.__end_callback is not None:
            self.__end_callback(self.__taskid)

    def file_progress_callback(self, filename:str, size:float, sent:float):
        self.__owner.update(self.__taskid, completed=sent)
        if sent == size:
            self.end()

class FileTransferProgress():
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

    def __init__(self, file, user:str, hostname:str):
        self.__richfileprogress = FileTransferProgress.getLayout()

        self.__tasks = {}
        self.__user = user
        self.__hostname = hostname

        if file is not None:
            if type(file) == str:
                self.add_file(file)
            if type(file) == list:
                [self.add_file(file) for file in file]

    def add_file(self, file:str):
        task = FileTransferTask(self.__richfileprogress, file, self.__user, self.__hostname)
        self.__tasks[task.name] = task

    def start(self):
        self.__richfileprogress.start()
        [t.start() for t in self.__tasks.values()]

    def stop(self):
        [t.stop() for t in self.__tasks.values()]
        self.__richfileprogress.stop()

    def file_progress_callback(self, filename:str, size:float, sent:float):
        self.__tasks[filename.decode("utf-8")].file_progress_callback(filename, size, sent)

    def set_filesent_callback(self, func):
        func(self)


"""
class DirectoryTransferProgress():
    def __init__(self, dir:str, files:'List[str]', user:str, hostname:str):
        self.__overallrichprogress = Progress(
	        SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TextColumn("[bold green]{task.fields[user]}@{task.fields[hostname]}"))

        self.__richfileprogress = Progress(
            TextColumn("\t├─"),
	        SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn())

        self.__tasks = {}
        self.__user = user
        self.__hostname = hostname
        self.__taskid = self.__overallrichprogress.add_task(
                            description = "[red]Downloading...", 
                            filename=dir, start=False, user=user, hostname=hostname)

        if files is not None:
            if type(files) == str:
                self.add_file(files)
            if type(files) == list:
                [self.add_file(file) for file in files]

    def add_file(self, file:str):
        task = FileTransferTask(self.__richfileprogress, file, self.__user, self.__hostname)
        self.__tasks[task.name] = task

    def start(self):
        self.__overallrichprogress.start()
        self.__overallrichprogress.start_task(self.__taskid)
        self.__richfileprogress.start()
        [t.start() for t in self.__tasks.values()]

    def stop(self):
        [t.stop() for t in self.__tasks.values()]
        self.__richfileprogress.stop()
        self.__overallrichprogress.stop_task(self.__taskid)
        self.__overallrichprogress.stop()

    def file_progress_callback(self, filename:str, size:float, sent:float):
        self.__tasks[filename.decode("utf-8")].file_progress_callback(filename, size, sent)

    def set_filesent_callback(self, func):
        func(self)
"""