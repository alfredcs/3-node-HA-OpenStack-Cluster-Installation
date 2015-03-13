#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncControl(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        cfgm_ip = self._args.cfgm_ip
        collector_ip = self._args.collector_ip
        self_ip = self._args.self_ip

        setup_args_str = "--role control"
        setup_args_str = setup_args_str + " --cfgm_ip %s --collector_ip %s --discovery_ip %s --control_ip %s" \
                                                      %(cfgm_ip, collector_ip, cfgm_ip, self_ip)
        if self._args.use_certs:
            setup_args_str = setup_args_str + " --use_certs"
            if self._args.puppet_server:
                setup_args_str = setup_args_str + " --puppet_server %s" %(self._args.puppet_server)

        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-control.py --cfgm_ip 10.1.5.11 --collector_ip 10.1.5.11
                                        --discovery_ip 10.1.5.11 --self_ip 10.1.5.12
                --use_certs --puppet_server a3s19.contrail.juniper.net
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'cfgm_ip': '127.0.0.1',
            'collector_ip': '127.0.0.1',
            'discovery_ip': '127.0.0.1',
            'self_ip': '127.0.0.1',
            'use_certs': False,
            'puppet_server': None,
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

        parser.add_argument("--cfgm_ip", help = "IP Address of the openstack controller")
        parser.add_argument("--collector_ip", help = "IP Address of the VNC collector")
        parser.add_argument("--discovery_ip", help = "IP Address of the VNC discovery server")
        parser.add_argument("--self_ip", help = "IP Address of the VNC control node")
        parser.add_argument("--use_certs", help = "Use certificates for authentication",
            action="store_true")
        parser.add_argument("--puppet_server", help = "FQDN of Puppet Master")

        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncControl

def main(args_str = None):
    SetupVncControl(args_str)
#end main

if __name__ == "__main__":
    main() 
