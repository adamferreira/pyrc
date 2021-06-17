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

class FileProgressEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)
        self.__progress = pyprogress.FileTransferProgress(*args, self.caller.user, self.caller.hostname)

    def transfer_begin(self, *args, **kwargs):
        return self.__progress.start()

    def transfer_end(self, *args, **kwargs):
        return self.__progress.stop()

    def progress(self, *args, **kwargs):
        return self.__progress_scp(args[0], args[1], args[2])

    def __progress_scp(self, filename:str, size:float, sent:float):
        return self.__progress.file_progress_callback(filename, size, sent)

