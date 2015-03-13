#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncCollector(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        setup_args_str = "--role collector"
        setup_args_str = setup_args_str + " --cassandra_ip_list %s" \
                             %(' '.join(self._args.cassandra_ip_list)) 
        if self._args.num_nodes:
            setup_args_str = setup_args_str + " --num_collector_nodes %d" \
                                 % (self._args.num_nodes)

        if self._args.cfgm_ip:
            setup_args_str = setup_args_str + " --cfgm_ip %s" \
                                 % (self._args.cfgm_ip)                                                   
        if self._args.self_collector_ip:
            setup_args_str = setup_args_str + " --self_collector_ip %s" \
                                 % (self._args.self_collector_ip)                                                   
        if self._args.analytics_data_ttl is not None:
            setup_args_str = setup_args_str + " --analytics_data_ttl %d" \
                                 % (self._args.analytics_data_ttl)                                                   
        if self._args.analytics_syslog_port is not None:
            setup_args_str = setup_args_str + " --analytics_syslog_port %d" \
                                 % (self._args.analytics_syslog_port)                                                   
        if self._args.internal_vip:
            setup_args_str = setup_args_str + " --internal_vip %s " % self._args.internal_vip

        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-collector.py --cassandra_ip_list 10.1.1.1 10.1.1.2 
            --cfgm_ip 10.1.5.11 --self_collector_ip 10.1.5.11 
            --analytics_data_ttl 1 --analytics_syslog_port 3514
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
        parser.add_argument("--cassandra_ip_list", help = "List of IP Addresses of cassandra nodes",
                            nargs='+', type=str)
        parser.add_argument("--cfgm_ip", help = "IP Address of the config node")
        parser.add_argument("--self_collector_ip", help = "IP Address of the collector node")
        parser.add_argument("--num_nodes", help = "Number of collector nodes", type = int)
        parser.add_argument("--analytics_data_ttl", help = "TTL in hours of data stored in cassandra database", type = int)
        parser.add_argument("--analytics_syslog_port", help = "Listen port for analytics syslog server", type = int)
        parser.add_argument("--internal_vip", help = "Internal VIP Address of openstack nodes")
        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncCollector

def main(args_str = None):
    SetupVncCollector(args_str)
#end main

if __name__ == "__main__":
    main()
