import re
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
