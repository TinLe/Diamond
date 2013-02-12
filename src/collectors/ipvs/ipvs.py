# coding=utf-8

"""
Shells out to get ipvs statistics, which may or may not require sudo access

Config is IPVSCollector.conf, most likely in /etc/diamond/collectors.


#### Dependencies

 * /usr/sbin/ipvsadmin

"""

import diamond.collector
import subprocess
import os
import string

# from diamond.metric import Metric
import diamond.convertor


class IPVSCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(IPVSCollector, self).get_default_config_help()
        config_help.update({
            'bin': 'Path to ipvsadm binary',
            'use_sudo': 'Use sudo?',
            'sudo_cmd': 'Path to sudo',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(IPVSCollector, self).get_default_config()
        config.update({
            'bin':              '/sbin/ipvsadm',
            'use_sudo':         False,
            'sudo_cmd':         '/usr/bin/sudo',
            'path':             'ipvs'
        })
        return config

    def collect(self):
        self.log.info( "ipvs: in collect()")
        if (not os.access(self.config['bin'], os.X_OK) or (self.config['use_sudo']
                and not os.access(self.config['sudo_cmd'], os.X_OK))):
            self.log.error("ipvs: unable to access %s" % (self.config['bin']))
            return

        command = [self.config['bin'], '--list',
                   '--stats', '--numeric']

        if self.config['use_sudo']:
            command.insert(0, self.config['sudo_cmd'])

        self.log.debug( "ipvs: before calling subprocess")
        try:
            p = subprocess.Popen(command, bufsize=-1,
                             stdout=subprocess.PIPE).communicate()[0][:-1]
        except:
            self.log.error("ipvs: unable to subprocess.Popen(%s)" % (command))
            return

        columns = {
            'conns': 2,
            'inpkts': 3,
            'outpkts': 4,
            'inbytes': 5,
            'outbytes': 6,
        }

        external = ""
        backend = ""
        self.log.debug( "ipvs: p=%s" % (p))
        for i, line in enumerate(p.split("\n")):
            self.log.debug( "ipvs: line=%s" % (line))
            if i < 3:
                continue
            row = line.split()

            if row[0] == "TCP" or row[0] == "UDP":
                external = string.replace(row[1], ".", "_")
                backend = "total"
            elif row[0] == "->":
                backend = string.replace(row[1], ".", "_")
            else:
                continue

            for metric, column in columns.iteritems():
                metric_name = ".".join([external, backend, metric])
                value = row[column]
                if (value.endswith('K')):
                    metric_value = int(value[0:len(value)-1]) * 1024
                elif (value.endswith('M')):
                    metric_value = int(value[0:len(value)-1]) * 1024 * 1024
                elif (value.endswith('G')):
                    metric_value = int(value[0:len(value)-1]) * 1024 * 1024 * 1024
                else:
                    metric_value = int(value)

                self.publish(metric_name, metric_value)
