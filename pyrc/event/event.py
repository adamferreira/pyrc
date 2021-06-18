import rich
import pyrc.event.progress as pyprogress

class Event(object):
    @property
    def caller(self):
        return self.__caller

    def __init__(self, caller, *args, **kwargs):
        self.__caller = caller 

class CommandEvent(Event):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(self, caller) 

    def new_line(self, line:str):
        print(line)

    def submitted(self, cmd, stdin, stdout, stderr):
        for line in stdout.readline():
            self.new_line(line)

class FileTransferEvent(Event):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller) 

    def transfer_begin(self, *args, **kwargs):
        return None

    def transfer_end(self, *args, **kwargs):
        return None

    def progress(self, *args, **kwargs):
        return None

class RichRemoteFileTransferEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)
        self.__progress = None

    def transfer_begin(self, *args, **kwargs):
        self.__progress = pyprogress.RemoteFileTransfer(*args, self.caller.user, self.caller.hostname)
        return self.__progress.start()

    def transfer_end(self, *args, **kwargs):
        return self.__progress.stop()

    def progress(self, *args, **kwargs):
        return self.__progress_scp(args[0], args[1], args[2])

    def __progress_scp(self, filename:str, size:float, sent:float):
        return self.__progress.file_progress_callback(filename, size, sent)

class RichRemoteDirTransferEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)

    def transfer_begin(self, *args, **kwargs):
        __local_dir = args[0]
        __remote_dir = args[1]
        rich.print(f"Uploading directory {__local_dir} to {self.caller.user}@{self.caller.hostname}:{__remote_dir}")
