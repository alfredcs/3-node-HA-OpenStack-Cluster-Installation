#!/usr/bin/python
import argparse
import ConfigParser

import os
import sys
import subprocess
from pprint import pformat

from fabric.api import local, env, run
from fabric.operations import get, put
from fabric.context_managers import lcd, settings
sys.path.insert(0, os.getcwd())

# set livemigration configurations in nova and libvirtd
class SetupLivem(object):

    def __init__(self, args_str = None):
        #print sys.argv[1:]
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        if self._args.storage_setup_mode == 'unconfigure':
            return

        NOVA_CONF='/etc/nova/nova.conf'
        LIBVIRTD_CONF='/etc/libvirt/libvirtd.conf'
        LIBVIRTD_TMP_CONF='/tmp/libvirtd.conf'
        LIBVIRTD_CENTOS_BIN_CONF='/etc/sysconfig/libvirtd'
        LIBVIRTD_UBUNTU_BIN_CONF='/etc/default/libvirt-bin'
        LIBVIRTD_TMP_BIN_CONF='/tmp/libvirtd.tmp'

        for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
           if entries != self._args.storage_master:
               with settings(host_string = 'root@%s' %(entries), password = entry_token):
                   if self._args.add_storage_node:
                       if self._args.add_storage_node != hostname:
                           continue
                   run('openstack-config --set %s DEFAULT live_migration_flag VIR_MIGRATE_UNDEFINE_SOURCE,VIR_MIGRATE_PEER2PEER,VIR_MIGRATE_LIVE' %(NOVA_CONF))
                   run('openstack-config --set %s DEFAULT vncserver_listen 0.0.0.0' %(NOVA_CONF))
                   run('cat %s | sed s/"#listen_tls = 0"/"listen_tls = 0"/ | sed s/"#listen_tcp = 1"/"listen_tcp = 1"/ | sed s/\'#auth_tcp = "sasl"\'/\'auth_tcp = "none"\'/ > %s' %(LIBVIRTD_CONF, LIBVIRTD_TMP_CONF), shell='/bin/bash')
                   run('cp -f %s %s' %(LIBVIRTD_TMP_CONF, LIBVIRTD_CONF))
                   libvirtd = run('ls %s 2>/dev/null |wc -l' %(LIBVIRTD_CENTOS_BIN_CONF))
                   if libvirtd != '0':
                       run('cat %s | sed s/"#LIBVIRTD_ARGS=\"--listen\""/"LIBVIRTD_ARGS=\"--listen\""/ > %s' %(LIBVIRTD_CENTOS_BIN_CONF, LIBVIRTD_TMP_BIN_CONF), shell='/bin/bash')
                       run('cp -f %s %s' %(LIBVIRTD_TMP_BIN_CONF, LIBVIRTD_CENTOS_BIN_CONF))
                       run('service openstack-nova-compute restart')
                       run('service libvirtd restart')

                   libvirtd = run('ls %s 2>/dev/null |wc -l' %(LIBVIRTD_UBUNTU_BIN_CONF))
                   if libvirtd != '0':
                       libvirt_configured = run('cat %s |grep "\-d \-l"| wc -l' %(LIBVIRTD_UBUNTU_BIN_CONF))
                       if libvirt_configured == '0':
                           run('cat %s | sed s/"-d"/"-d -l"/ > %s' %(LIBVIRTD_UBUNTU_BIN_CONF, LIBVIRTD_TMP_BIN_CONF), shell='/bin/bash')
                           run('cp -f %s %s' %(LIBVIRTD_TMP_BIN_CONF, LIBVIRTD_UBUNTU_BIN_CONF))
                           run('service nova-compute restart')
                           run('service libvirt-bin restart')

    def _parse_args(self, args_str):
        '''
        Eg. python compute-live-migration-setup.py --storage-master 10.157.43.171 --storage-hostnames cmbu-dt05 cmbu-ixs6-2 --storage-hosts 10.157.43.171 10.157.42.166 --storage-host-tokens n1keenA n1keenA 
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            global_defaults.update(dict(config.items("GLOBAL")))

        # Override with CLI options
        # Don't surpress add_help here so it will handle -h
        parser = argparse.ArgumentParser(
            # Inherit options from config_parser
            parents=[conf_parser],
            # print script description with -h/--help
            description=__doc__,
            # Don't mess with format of description
            formatter_class=argparse.RawDescriptionHelpFormatter,
            )

        all_defaults = {'global': global_defaults}
        parser.set_defaults(**all_defaults)

        parser.add_argument("--storage-master", help = "IP Address of storage master node")
        parser.add_argument("--storage-hostnames", help = "Host names of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-hosts", help = "IP Addresses of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-host-tokens", help = "Passwords of storage nodes", nargs='+', type=str)
        parser.add_argument("--add-storage-node", help = "Add a new storage node")
        parser.add_argument("--storage-setup-mode", help = "Storage configuration mode")

        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

def main(args_str = None):
    SetupLivem(args_str)
#end main

if __name__ == "__main__":
    main() 
