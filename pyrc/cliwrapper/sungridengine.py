import re, time
import pyrc.system as pysys
import pyrc.event as pyevent

from pyrc.system import FileSystem
from pyrc.cliwrapper import CLIWrapper

class SunGridEngine(CLIWrapper):
    def __init__(self, connector:FileSystem = None, workdir:str = "") -> None:
        super().__init__("", connector, workdir)
        # TODO : Remove environment and cwd from commands ?

    @staticmethod
    def get_submission_info(line:str) -> 'tuple[str,str]':
        m = re.match("Your job (?P<jid>([0-9]+)) \(\"(?P<name>(.)*)\"\) has been submitted", line)
        if m is None:
            return None, None
        else:
            return m.group("jid"), m.group("name")

    # tips for selecting specific sge id : qstat | grep "^[[:space:]]*$ID[[:space:]]"
    def __fancyqstatcmd(flags: 'list[str]' = [], job_prefix: str = None) -> 'str':
        """
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
                job_prefix (str, optional): [description]. Defaults to None.
            Returns:
                str: [description]
        """
        qstat_cmd = "qstat -xml "
        qstat_cmd += " ".join(flags)
        qstat_cmd += " | tr \'\\n\' \' \' |"
        qstat_cmd += " sed \'s#<job_list[^>]*>#\\n#g\'| "
        qstat_cmd += " sed \'s#<[^>]*>##g\' |"
        qstat_cmd += " grep \" \" | column -t"

        if job_prefix is not None:
            qstat_cmd += " | grep \"" + str(job_prefix) + "\""

        return qstat_cmd

    def qstat(self, flags: 'list[str]' = [], job_prefix: str = None, cwd:str = "", environment:dict = None) -> 'list[dict[str:str]]':
        """
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
        Returns:
            [type]: [description]
        """

        assert self.connector.is_unix()
        jobs = []
        qstatlines, errors, status = self.connector.exec_command(
            cmd = SunGridEngine.fancyqstatcmd(flags, job_prefix),
            cwd = cwd,
            environment = environment,
            event = pyevent.CommandStoreEvent(self.connector) # hard coded store event
        )

        for line in qstatlines:
            if line == "" : break
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

    def wait(self, jid:str, refresh:int=30):
        job_info = SunGridEngine.qstat(self.connector, job_prefix=jid)
        while len(job_info) > 0:
            time.sleep(refresh)
            job_info = SunGridEngine.qstat(self.connector, job_prefix=jid)

    def qsub(
        self,
        bash_script:str,
        jobname:str = None,
        script_parameters:'str' = [],
        env_vars:'list[str]' = [],
        working_directory:str = None,
        maximum_run_time:str = "168:00:00",
        queue:str = None,
        log_file:str = None,
        err_file:str = None,
        mail:str = None,
        parallel_env:str = None,
        on_hold:bool = False,
        wait:'list[str]' = [],
        event:pyevent.CommandStoreEvent = None,
    ) -> str:
	    # For some reason SGE is using its own script interpreter
	    # Which is not exactly bash syntax and may require using 'sed'
	    # Tu use the systems' bash use the flag : -S /bin/bash
	    # or #$ -S /bin/bash  INSIDE the script
        qsubcmd = "qsub"
        qsubcmd += f" -h" if on_hold else ""
        qsubcmd += f" -pe {parallel_env}" if (parallel_env is not None) else ""
        qsubcmd += f" -q {queue}" if (queue is not None) else ""
        qsubcmd += f" -N {jobname}" if (jobname is not None) else ""
        qsubcmd += f" -o {log_file}" if (log_file is not None) else ""
        qsubcmd += f" -e {err_file}" if (err_file is not None) else ""
        qsubcmd += f" -l h_rt={maximum_run_time}"
        qsubcmd += f" -wd {working_directory}" if (working_directory is not None) else " -cwd "
        qsubcmd += f" -m ea -M {mail}" if (mail is not None) else ""

        qsubcmd += (" -v " + ",".join(env_vars)) if (len(env_vars) > 0) else ""
        qsubcmd += (" -hold_jid " + ",".join(wait)) if (len(wait) > 0) else ""

        qsubcmd += f" {bash_script}"
        qsubcmd += (" " + " ".join(script_parameters)) if (len(script_parameters) > 0) else ""

        out, err, _ = self.connector.exec_command(
            cmd = qsubcmd,
            cwd = "" if working_directory is None else working_directory,
            environment = None, # Qsub doesnt need env to be launch as the script run in separate shell env,
            event = pyevent.CommandPrettyPrintEvent(self.connector, print_input=True, print_errors=True) if (event is None) else event
        )   
        assert len(err) == 0
        jid, jname = SunGridEngine.get_submission_info(out[0])

        return jid