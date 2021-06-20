import rich
import pyrc.event.progress as pyprogress

class Event(object):
    @property
    def caller(self):
        return self.__caller

    def __init__(self, caller, *args, **kwargs):
        self.__caller = caller 

    def begin(self, *args, **kwargs):
        return None

    def end(self, *args, **kwargs):
        return None

    def progress(self, *args, **kwargs):
        return None

class CommandPrintEvent(Event):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller) 

    def progress(self, line):
        print(line)

    def begin(self, cmd, stdin, stdout, stderr):
        print(f"{self.caller.user}@{self.caller.hostname} -> {cmd}")
        while not stdout.channel.exit_status_ready():
            self.progress(stdout.readline().strip('\n'))

class CommandStoreEvent(Event):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)
        self.__lines = [] 
        
    def begin(self, cmd, stdin, stdout, stderr):
        self.__lines = stdout.read().decode("utf-8").strip('\n').split('\n')

    def end(self):
        return self.__lines


class FileTransferEvent(Event):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller) 

class RichRemoteFileTransferEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)
        self.__progress = None

    def begin(self, *args, **kwargs):
        self.__progress = pyprogress.RemoteFileTransfer(*args, self.caller.user, self.caller.hostname)
        return self.__progress.start()

    def end(self, *args, **kwargs):
        return self.__progress.stop()

    def progress(self, *args, **kwargs):
        self.__progress.file_progress(filename = args[0], size = args[1], sent = args[2])

class RichRemoteDirUploadEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)

    def begin(self, *args, **kwargs):
        __local_dir = args[0]
        __remote_dir = args[1]
        rich.print(f"Uploading directory {__local_dir} to {self.caller.user}@{self.caller.hostname}:{__remote_dir}")

class RichRemoteDirDownloadEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)

    def begin(self, *args, **kwargs):
        __local_dir = args[0]
        __remote_dir = args[1]
        rich.print(f"Downloading directory {self.caller.user}@{self.caller.hostname}:{__remote_dir} to {__local_dir}")