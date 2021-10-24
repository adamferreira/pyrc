import pyrc.system as pysys

class BashScriptGenerator(pysys.FileSystem):
    def __init__(self, script_path:str):
        # Do not call parents constructor as it will auto-detect the local OS !
        #super().__init__(remote = None)

        # Fake connect to trick this object into thinking is connected somewhere
        # This will cause every Filesystem command to be a remote (unix) command call
        # (That we can capture by overriding exec_command), as every remote event on FileSystem calls exec_command
        # For example, with this trick :
        # self.isdir(dir) will call overrided 'exec_command' with unix command '[[ -s dir ]] && echo "ok"'
        # And we can capture this command, and not launch it
        self.set_connector("")

        # Trick this object to think the 'remote' filesystem is unix
        # As we seek bash language file
        self.ostype = pysys.OSTYPE.LINUX


        # Local filesystem to check given script path
        self.__local_path = pysys.FileSystem()
        self.script = None
        assert self.__local_path.isdir(self.__local_path.dirname(script_path))
        self.script = open(script_path, "w+")
        self.__last_printed_env:str = ""

    def __del__(self):
        if self.script is not None:
            self.script.close()

    # Capture the command that would have been called remotely, and store it in the bash file
    # Not event call here !
    def exec_command(self, cmd:str, cwd:str = "", environment:dict = None, event = None):
        
        if environment is not None:
            # Do not reprint envs var is its the same than last call
            # Because PATH=<vars>:PATH would became VERY long if called to many times
            if self.__last_printed_env != str(environment):
                self.script.writelines([f"export {var}={val}\n" for var,val in environment.items()])
                self.script.writelines(["\n"])
                self.__last_printed_env = str(environment)

        self.script.writelines([
            f"cd {cwd}\n",
            f"{cmd}\n",
            "\n"
        ])

        # Trick so that 'isdir', 'isfile', etc always returns 'True'
        # Because the connection is fake and pyrc-using python scripts would like to use those check
        # when using genuine remote connector
        # stdout = ["ok"], stderr = []
        return ["ok"], []