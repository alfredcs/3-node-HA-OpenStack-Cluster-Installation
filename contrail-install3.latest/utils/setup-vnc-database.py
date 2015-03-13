#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncDatabase(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
       
        self_ip = self._args.self_ip
        dir = self._args.dir
        data_dir = self._args.data_dir
        initial_token = self._args.initial_token
        seed_list = self._args.seed_list
        analytics_data_dir = self._args.analytics_data_dir
        ssd_data_dir = self._args.ssd_data_dir
        
        setup_args_str = "--role database"
        setup_args_str = setup_args_str + " --database_listen_ip %s" \
                             % (self_ip)
        if dir:                     
            setup_args_str = setup_args_str + " --database_dir %s" \
                                 % (dir)
        if data_dir:                     
            setup_args_str = setup_args_str + " --data_dir %s" \
                                 % (data_dir)
        if analytics_data_dir:                     
            setup_args_str = setup_args_str + " --analytics_data_dir %s" \
                                 % (analytics_data_dir)
        if ssd_data_dir:                     
            setup_args_str = setup_args_str + " --ssd_data_dir %s" \
                                 % (ssd_data_dir)
        if initial_token:
            setup_args_str = setup_args_str + " --database_initial_token %s" \
                                 % (initial_token)
        if seed_list:
            setup_args_str = setup_args_str + " --database_seed_list %s" % (' '.join(seed_list))                                                                       
	if self._args.cfgm_ip:
            setup_args_str = setup_args_str + " --cfgm_ip %s" \
                                 % (self._args.cfgm_ip)
        setup_args_str = setup_args_str + " --zookeeper_ip_list %s" \
                             %(' '.join(self._args.zookeeper_ip_list))
        setup_args_str = setup_args_str + " --database_index %s" \
                             %(self._args.database_index)

        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-database.py
            --self_ip 10.84.13.23
            --dir /usr/share/cassandra
            --initial_token 0 --seed_list 10.84.13.23 10.84.13.24
            --data_dir /home/cassandra
            --zookeeper_ip_list 10.1.5.11 10.1.5.12
            --database_index 1
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
        parser.add_argument("--self_ip", help = "IP Address of this database node")
        parser.add_argument("--cfgm_ip", help = "IP Address of the config node")
        parser.add_argument("--dir", help = "Directory where database binary exists")
        parser.add_argument("--initial_token", help = "Initial token for database node")
        parser.add_argument("--seed_list", help = "List of seed nodes for database", nargs='+')
        parser.add_argument("--data_dir", help = "Directory where database stores data")
        parser.add_argument("--analytics_data_dir", help = "Directory where database stores analytics data")
        parser.add_argument("--ssd_data_dir", help = "SSD directory that database stores data")
        parser.add_argument("--zookeeper_ip_list", help = "List of IP Addresses of zookeeper servers",
                            nargs='+', type=str)
        parser.add_argument("--database_index", help = "The index of this databse node")
        self._args = parser.parse_args(remaining_argv)
    #end _parse_args

#end class SetupVncDatabase

def main(args_str = None):
    SetupVncDatabase(args_str)
#end main

if __name__ == "__main__":
    main()
