from typing import Generator
import rich
from rich.console import Console
from pyrc.event.progress import RemoteFileTransfer

class RemoteSSHFileSystem:pass


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class FluxIterator:
    @staticmethod
    def next(flux) -> str:
        # If the flux is not we generator
        # We assume is a pipe-style object like in paramiko or subprocess
        if flux is None: return None
        out:str = None
        if isinstance(flux, Generator):
            try:
                out = next(flux)
            except:
                return None
        else:
            out = flux.readline()
            if not out : return None

        if out is None : return None
        
        if type(out) != str:
            out = out.decode("utf-8")
        return out.strip('\n')

    def __init__(self, flux):
        self._flux = flux

    def __iter__(self):
        return self

    def __next__(self): # Python 2: def next(self)
        n = FluxIterator.next(self._flux)
        if n is None:
            raise StopIteration
        return n

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

class EventFlux(Event):

    def __init__(self, caller, *args, **kwargs):
        Event.__init__(self, caller)
        self._stdinflux = None
        self._stdoutflux = None
        self._stderrflux = None

    def begin(self, cmd, cwd, stdin, stdout, stderr):
        self._stdinflux = stdin
        self._stdoutflux = stdout
        self._stderrflux = stderr

    def next_stdout(self) -> str:
        return FluxIterator.next(self._stdoutflux)

    def next_stderr(self) -> str:
        return FluxIterator.next(self._stderrflux)

    def status(self):
        # Only check status when using paramiko channels
        # It is only used because paramiko tends to feed errors even for non 0 status
        # This does not occurs with other librarys
        if type(self._stdoutflux) == 'ChannelFile':
            return self._stdoutflux.channel.recv_exit_status()
        else: # defulat status is 'ok' status
            return 0

class CommandStorer(EventFlux):
    """
    Base Event used to store captured stdout and stderr of a launched command.
    end() returns all stdout and stderr lines captured.
    """
    @property
    def cmd(self):
        return self.__cmd

    @property
    def cwd(self):
        return self.__cwd

    def __init__(self, caller, *args, **kwargs):
        EventFlux.__init__(self, caller)
        self.__stdout:'list[str]' = [] 
        self.__stderr:'list[str]' = []
        self.__cmd:str = ""
        self.__cwd:str = ""

    def begin(self, cmd, cwd, stdin, stdout, stderr):
        EventFlux.begin(self, cmd, cwd, stdin, stdout, stderr)
        self.__cmd = cmd
        self.__cwd = cwd

    def progress(self, stdoutline:str, stderrline:str):
        if stdoutline != "":
            self.__stdout.append(stdoutline)

        if stderrline != "":
            self.__stdout.append(stderrline)

    def end(self):
        return self.__stdout, self.__stderr, self.status()


#for line in stdout:
#    self.progress(line.decode("utf-8").rstrip())
#    stdout.flush()
# Poll process.stdout to show stdout live
#while True:
#    output = process.stdout.readline()
#    if process.poll() is not None:
#        break
#    if output:
#        self.progress(output.strip())
#rc = process.poll()
class CommandScrapper2(Event):
    def __init__(self, caller = None, *args, **kwargs):
        Event.__init__(self, caller)
        self._errflux = None

    def begin(self, cmd, cwd, stdin, stdout, stderr):
        # For some reason we cannot read stdout and stderr at the same time
        # It will work but some stdout line would be missed !
        # So we read all stdout first, then all stderr
        self._errflux = stderr
        while True:
            out = EventFlux.next_flux(stdout)
            if out is None : break
            self.progress(
                stdoutline = out,
                stderrline = ""
                )

    def end(self):
        while True:
            out = EventFlux.next_flux(self._errflux)
            if out is None : break
            self.progress(
                stdoutline = "",
                stderrline = out, 
                )

class CommandScrapper(Event):
    def __init__(self, caller, *args, **kwargs):
        Event.__init__(self, caller)
        self._errit = None

    def begin(self, cmd, cwd, stdin, stdout, stderr):
        self._errit = FluxIterator(stderr)
        for out in FluxIterator(stdout):
            self.progress(stdoutline = out, stderrline = "")

    def end(self):
        for out in self._errit:
            self.progress(stdoutline = out, stderrline = "")


class CommandStoreEvent(CommandStorer, CommandScrapper):
    def __init__(self, caller = None, *args, **kwargs):
        CommandStorer.__init__(self, caller)
        CommandScrapper.__init__(self, caller)

    def progress(self, stdoutline:str, stderrline:str):
        CommandStorer.progress(self, stdoutline, stderrline)

    def begin(self, cmd, cwd, stdin, stdout, stderr):
        CommandStorer.begin(self, cmd, cwd, stdin, stdout, stderr)
        CommandScrapper.begin(self, cmd, cwd, stdin, stdout, stderr)

    def end(self):
        # Read and store errors
        CommandScrapper.end(self)
        return CommandStorer.end(self)

class ErrorRaiseEvent(CommandStoreEvent):
    def __init__(self, caller = None, *args, **kwargs):
        CommandStoreEvent.__init__(self, caller)

    def end(self):
        out, err, status = CommandStoreEvent.end(self)
        if len(err) > 0:
            raise RuntimeError("\n".join(err))
        return  out, err, status


class CommandPrettyPrintEvent(CommandStoreEvent):
    def __init__(
            self, 
            caller, 
            print_input = True, 
            print_errors = False, 
            use_rich = True, 
            *args, 
            **kwargs
        ):
        CommandStoreEvent.__init__(self, caller)
        self._print_input = print_input
        self._print_errors = print_errors
        self._use_rich = use_rich
        self.console = Console() if self._use_rich else None


    def __callerline(self, line:str) -> None:
        if self._use_rich:
            self.console.print(line, style ="bright_green", end=":")
        else:
            print(bcolors.OKGREEN + line + bcolors.ENDC, end=":")

    def __cmdline(self, line:str) -> None:
        line = f"$({line})"
        if self._use_rich:
            self.console.print(f"[deep_pink3]{line}[/deep_pink3]") #magenta3
            #self.console.print(line, style ="deep_pink4")
        else:
            print(bcolors.HEADER + line + bcolors.ENDC)

    def __dirline(self, line:str) -> None:
        if self._use_rich:
           self.console.print(line, style ="dodger_blue3", end = " -> ")
        else:
            print(bcolors.OKBLUE + line + bcolors.ENDC, end = " -> ")
    

    def begin(self, cmd, cwd, stdin, stdout, stderr):
        if self._print_input:
            if isinstance(self.caller, RemoteSSHFileSystem):
                self.__callerline(f"{self.caller.user}@{self.caller.hostname}")
            else:
                self.__callerline(f"{type(self.caller)}")
            
            self.__dirline(cwd)
            self.__cmdline(cmd)

        CommandStoreEvent.begin(self, cmd, cwd, stdin, stdout, stderr)

    def progress(self, stdoutline:str, stderrline:str):
        CommandStoreEvent.progress(self, stdoutline, stderrline)
        
        if stdoutline != "":
            if self._use_rich:
                rich.print(("\t" if self._print_input else "") + stdoutline)
            else:
                print(("\t" if self._print_input else "") + stdoutline)
            
        if stderrline != "" and self._print_errors:
            # Sometime a log of-non erros logs (warnings for example) ends up in the error flux
            # We only print them as error if the status of the sydout channel is not 0
            # Also we only evaluate the status here as stdout is printed in real-time
            # But errors are printed when the command as terminated
            if self.status() != 0:
                print(bcolors.FAIL + ("\t" if self._print_input else "") + "[ERROR]", stderrline + bcolors.ENDC)
        
    def end(self):
        out, err, status = CommandStoreEvent.end(self)
        return out, err, status


class FileTransferEvent(Event):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller) 

class RichRemoteFileTransferEvent(FileTransferEvent):
    def __init__(self, caller, *args, **kwargs):
        super().__init__(caller)
        self.__progress = None

    def begin(self, *args, **kwargs):
        self.__progress = RemoteFileTransfer(*args, self.caller.user, self.caller.hostname)
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