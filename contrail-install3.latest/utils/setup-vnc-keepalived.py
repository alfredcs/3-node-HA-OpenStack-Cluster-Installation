#!/usr/bin/python
#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import KeepalivedSetup

class SetupVncKeepalived(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        role = self._args.role
        self_ip = self._args.self_ip
        internal_vip = self._args.internal_vip
        self_index = self._args.self_index
        num_nodes = self._args.num_nodes

        setup_args_str = "--role %s " % role
        if role == 'openstack':
            setup_args_str = setup_args_str + " --openstack_ip %s " % (self_ip)
            setup_args_str = setup_args_str + " --openstack_index %s"  % (self_index)
        if role == 'cfgm':
            setup_args_str = setup_args_str + " --cfgm_ip %s " % (self_ip)
            setup_args_str = setup_args_str + " --cfgm_index %s"  % (self_index)
        setup_args_str = setup_args_str + " --internal_vip %s " % (internal_vip)
        setup_args_str = setup_args_str + " --num_nodes %s " % (num_nodes)
        if self._args.external_vip:
            setup_args_str = setup_args_str + " --external_vip %s " % (self._args.external_vip)
        if self._args.mgmt_self_ip:
            setup_args_str = setup_args_str + " --mgmt_self_ip %s " % (self._args.mgmt_self_ip)
        
        setup_obj = KeepalivedSetup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-keepalived.py --self_ip 10.1.5.11 --mgmt_self_ip 11.1.5.11
                   --self_index 1 --internal_vip 10.1.5.13 --external_vip 11.1.5.13
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'self_ip': '127.0.0.1',
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

        parser.add_argument("--role", help = "Role of the node")
        parser.add_argument("--self_ip", help = "IP Address of this system")
        parser.add_argument("--mgmt_self_ip", help = "Management IP Address of this system")
        parser.add_argument("--internal_vip", help = "Internal(private) Virtual IP Addresses of HA nodes"),
        parser.add_argument("--external_vip", help = "External(public) Virtual IP Addresses of HA nodes"),
        parser.add_argument("--self_index", help = "The index of this HA node")
        parser.add_argument("--num_nodes", help = "Number of available HA node")
        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncOpenstack

def main(args_str = None):
    SetupVncKeepalived(args_str)
#end main

if __name__ == "__main__":
    main() 
