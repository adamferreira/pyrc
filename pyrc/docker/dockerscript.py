from typing import Union, List
from pyrc.system import ScriptGenerator, OSTYPE

class DockerFile(ScriptGenerator):
	"""
	DockerFile is a ScriptGenerator that store dockerfile-like commands in a dockerfile
	"""
	def __init__(self, dockerfile:str, mode:str) -> None:
		ScriptGenerator.__init__(
			self,
			script_path = dockerfile,
			mode = mode,
			ostype = OSTYPE.LINUX
		)

	def _gerenate_cmd(self, flag:str, statements:Union[str, List[str]]):
		if isinstance(statements, str):
			return self._gerenate_cmd(flag, [statements])

		if len(statements) == 0: return self
		if len(statements) == 1:
			self.writeline(f"{flag} {statements[0]}")
		else:
			run = "; \ \n\t".join(statements)
			self.writeline(f"{flag} {run}")


	def append_dockerfile(self, dockerfile:str) -> "DockerFile":
		with open(dockerfile, 'r') as d:
			for line in d.readlines():
				line = line.strip("\n")
				self.writeline(line)


	def FROM(self, image:str) -> "DockerFile":
		self._gerenate_cmd(f"{self.FROM.__name__}", image)
		return self

	def RUN(self, statements:Union[str, List[str]]) -> "DockerFile":
		self._gerenate_cmd(f"{self.RUN.__name__}", statements)
		return self

	def USER(self, user:str) -> "DockerFile":
		self._gerenate_cmd(f"{self.USER.__name__}", user)
		return self

	def ENTRYPOINT(self, user:str) -> "DockerFile":
		self._gerenate_cmd(f"{self.ENTRYPOINT.__name__}", user)
		return self

	def ENV(self, var:str, value:str) -> "DockerFile":
		self._gerenate_cmd(f"{self.ENV.__name__}", f"{var} {value}")
		return self

	def CMD(self, cmd:str) -> "DockerFile":
		self._gerenate_cmd(f"{self.CMD.__name__}", f"[\"{cmd}\"]")
		return self

	def COPY(self, src:str, dest:str) -> "DockerFile":
		self._gerenate_cmd(f"{self.COPY.__name__}", f"{src} {dest}")
		return self

	def EXPOSE(self, port:int) -> "DockerFile":
		self._gerenate_cmd(f"{self.EXPOSE.__name__}", f"{port}")
		return self

class UnixDockerFile(DockerFile):
    def __init__(
            self,
            dockerfile:str,
            imgfrom:str,
            user:str
        ) -> None:
        super().__init__(dockerfile, "w+")

        # open file
        self.open()

        # From ubuntu 22 
        self.FROM(imgfrom)

        # Run eveything as root
        self.USER(f"{user}")

        # Pkg setup
        self.RUN([
            f"{self.__package_manager()} update -y",
            f"{self.__package_manager()} upgrade -y"
        ])

        self.image:str = imgfrom.split(":")[0]
        self.tag:str = imgfrom.split(":")[0]

    def __package_manager(self) -> str:
        prefix:str = "DEBIAN_FRONTEND=noninteractive"
        if "debian" in self.image:
            return f"{prefix} dpkg"

        if "ubuntu" in self.image:
            return f"{prefix} apt-get"

        if "fedora" in self.image:
            return f"{prefix} yum"

        if "alpine" in self.image:
            return f"{prefix} apk"

    def install(self, ubuntu_packages:List[str]) -> "UnixDockerFile":
        if isinstance(ubuntu_packages, str):
            return self.install([ubuntu_packages])

        if len(ubuntu_packages) == 0:
            return self
        
        if len(ubuntu_packages) == 1:
            self.RUN(
                f"{self.__package_manager()} install -y {ubuntu_packages[0]}" 
            )
        else:
            install = " \ \n\t".join(ubuntu_packages)
            self.RUN(
                f"{self.__package_manager()} install -y \ \n\t{install}" 
            )
        return self