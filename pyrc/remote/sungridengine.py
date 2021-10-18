import pyrc
from remotecon import SSHConnector

class SunGridEngineLauncher(object):
    def __init__(self):
        # CommandExecutor(self)
        self.sgecmd = pylc.SunGridEngineCommand()

    def qstat(self, flags: 'list[str]' = [], job_prefix: str = None, remote: SSHConnector = None, print_output: bool = False, print_input: bool = True) -> 'list[dict[str:str]]':
        """[summary]
            This perferms a formated qstats command on the remote machine.
            The format is the following : 
            qstat -xml | tr '\n' ' ' | sed 's#<job_list[^>]*>#\n#g'| sed 's#<[^>]*>##g' | grep " " | column -t
            Description of commands:
                List jobs as XML: qstat -xml
                Remove all newlines: tr '\n' ' '
                Add newline before each job entry in the list: sed 's#<job_list[^>]*>#\n#g'
                Remove all XML stuff: sed 's#<[^>]*>##g'
                Hack to add newline at the end: grep " "
                Columnize: column -t
        Args:
            flags (list[str], optional): [description]. Defaults to [].
            job_prefix (str, optional): [description]. Defaults to None.
            remote (bool, optional): [description]. Defaults to False.
            print_output (bool, optional): [description]. Defaults to False.
            print_input (bool, optional): [description]. Defaults to True.

        Returns:
            list[dict[str:str]]: [description]
        """
        jobs = []
        qstat_cmd = self.sgecmd.fancyqstatcmd(flags, job_prefix)
        qstatlines = self.exec_command(
            qstat_cmd, flags, remote, print_output, print_input)
            
        for line in qstatlines:
            infos = []
            for item in line.split(' '):
                if len(item) > 0:
                    infos.append(item.replace("\n", ""))

            jid = infos[0]
            jpriority = infos[1]
            jname = infos[2]
            juser = infos[3]
            jstate = infos[4]
            if len(infos) > 6:
                jsubmitdate = infos[5]
                jslot = infos[6]
            else:
                jsubmitdate = "pending"
                jslot = infos[5]

            jobs.append({
                "id": jid,
                "priority": jpriority,
                "name": jname,
                "user": juser,
                "state": jstate,
                "date": jsubmitdate,
                "slots": jslot
            })

        return jobs
