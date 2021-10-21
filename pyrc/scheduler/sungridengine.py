import re
import pyrc.system as pysys
import pyrc.event as pyevent
class SunGridEngine(object):

    def get_submission_info(line:str) -> 'tuple[str,str]':
        m = re.match("Your job (?P<jid>([0-9]+)) \(\"(?P<name>(.)*)\"\) has been submitted", line)
        if m is None:
            return None, None
        else:
            return m.group("jid"), m.group("name")


    # tips for selecting specific sge id : qstat | grep "^[[:space:]]*$ID[[:space:]]"
    def fancyqstatcmd(flags: 'list[str]' = [], job_prefix: str = None) -> 'str':
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

    def qstat(path:pysys.FileSystem, flags: 'list[str]' = [], job_prefix: str = None, cwd:str = "", environment:dict = None) -> 'list[dict[str:str]]':
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
        Returns:
            [type]: [description]
        """

        assert path.is_unix()
        jobs = []
        qstatlines = path.exec_command(
            cmd = SunGridEngine.fancyqstatcmd(flags, job_prefix),
            cwd = cwd,
            environment = environment,
            event = pyevent.CommandStoreEvent(path.connector) # hard coded store event
        )

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
    
