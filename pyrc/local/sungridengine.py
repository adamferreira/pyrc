    # tips for selecting specific sge id : qstat | grep "^[[:space:]]*$ID[[:space:]]"
    def qstat(self, flags:'list[str]' = [], remote:bool = False, print_output:bool = False, print_input:bool = True, job_prefix:str=None) -> 'list[str]':
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
            remote (bool, optional): [description]. Defaults to False.
            print_output (bool, optional): [description]. Defaults to False.
            print_input (bool, optional): [description]. Defaults to True.
            job_prefix (str, optional): [description]. Defaults to None.

        Returns:
            list[str]: [description]
        """
        jobs = []
        qstat_cmd = "qstat -xml"
        qstat_cmd += " | tr \'\\n\' \' \' |"
        qstat_cmd += " sed \'s#<job_list[^>]*>#\\n#g\'| "
        qstat_cmd += " sed \'s#<[^>]*>##g\' |"
        qstat_cmd += " grep \" \" | column -t"

        if job_prefix is not None:
            qstat_cmd += " | grep \"" + str(job_prefix) + "\""

        qstatlines = self.exec_command(qstat_cmd, flags, remote, print_output, print_input)
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
                "id" : jid,
                "priority" : jpriority,
                "name" : jname,
                "user": juser,
                "state" : jstate,
                "date" : jsubmitdate,
                "slots" : jslot 
            })
        
        return jobs
