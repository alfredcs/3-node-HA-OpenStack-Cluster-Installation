#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncCfgm(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        self_ip = self._args.self_ip
        keystone_ip = self._args.keystone_ip
        internal_vip = self._args.internal_vip
        collector_ip = self._args.collector_ip
        quantum_port = self._args.quantum_port
        nworkers = self._args.nworkers
        service_token = self._args.service_token
        region_name = self._args.region_name
        ks_auth_protocol = self._args.keystone_auth_protocol
        ks_auth_port = self._args.keystone_auth_port
        ks_admin_token = self._args.keystone_admin_token
        ks_insecure = self._args.keystone_insecure
        amqp_server_ip = self._args.amqp_server_ip

        setup_args_str = "--role config "
        setup_args_str = setup_args_str + " --cfgm_ip %s --keystone_ip %s --collector_ip %s " \
                                                      %(self_ip, keystone_ip, collector_ip)
        setup_args_str = setup_args_str + " --quantum_port %s" %(quantum_port)
        setup_args_str = setup_args_str + " --n_api_workers %s" %(nworkers)
        setup_args_str = setup_args_str + " --ks_auth_protocol %s" %(ks_auth_protocol)
        setup_args_str = setup_args_str + " --ks_auth_port %s" %(ks_auth_port)
        setup_args_str = setup_args_str + " --ks_admin_token %s" %(ks_admin_token)
        setup_args_str = setup_args_str + " --ks_insecure %s" %(ks_insecure)
        setup_args_str = setup_args_str + " --amqp_server_ip %s" %(amqp_server_ip)

        if service_token:
            setup_args_str = setup_args_str + " --service_token %s " %(service_token)
        if region_name:
            setup_args_str = setup_args_str + " --region_name %s " %(region_name)
        if self._args.use_certs:
            setup_args_str = setup_args_str + " --use_certs"
        if self._args.multi_tenancy:
            setup_args_str = setup_args_str + " --multi_tenancy"
        setup_args_str = setup_args_str + " --cassandra_ip_list %s" \
                             %(' '.join(self._args.cassandra_ip_list))    
        setup_args_str = setup_args_str + " --zookeeper_ip_list %s" \
                             %(' '.join(self._args.zookeeper_ip_list))    
        if self._args.haproxy:
            setup_args_str = setup_args_str + " --haproxy"
        if internal_vip:
            setup_args_str = setup_args_str + " --internal_vip %s " %(internal_vip)
        if self._args.manage_neutron == 'yes':
            setup_args_str = setup_args_str + " --manage_neutron"
        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-cfgm.py --self_ip 10.1.5.11 --keystone_ip 10.1.5.12 
            --collector_ip 10.1.5.12 --service_token contrail123
            --cassandra_ip_list 10.1.5.11 10.1.5.12 
            --zookeeper_ip_list 10.1.5.11 10.1.5.12
            --nworkers 1
            optional: --use_certs, --multi_tenancy --haproxy
                      --region_name <name> --internal_vip 10.1.5.100
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'self_ip': '127.0.0.1',
            'collector_ip': '127.0.0.1',
            'keystone_ip': '127.0.0.1',
            'service_token': '',
            'use_certs': False,
            'multi_tenancy': False,
            'nworkers': '1',
            'haproxy': False,
            'region_name': None,
            'ks_auth_protocol':'http',
            'ks_auth_port':'35357',
            'amqp_server_ip':'127.0.0.1'
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

        parser.add_argument("--self_ip", help = "IP Address of this system")
        parser.add_argument("--collector_ip", help = "IP Address of collector node")
        parser.add_argument("--keystone_ip", help = "IP Address of keystone node")
        parser.add_argument("--service_token", help = "The service password to access keystone")
        parser.add_argument("--use_certs", help = "Use certificates for authentication (irond)",
            action="store_true")
        parser.add_argument("--multi_tenancy", help = "Enforce resource permissions (implies token validation)",
            action="store_true")
        parser.add_argument("--cassandra_ip_list", help = "List of IP Addresses of cassandra nodes",
                            nargs='+', type=str)
        parser.add_argument("--zookeeper_ip_list", help = "List of IP Addresses of zookeeper servers",
                            nargs='+', type=str)
        parser.add_argument("--quantum_port",
            help = "Quantum Server port",
            default = '9696')
        parser.add_argument("--keystone_auth_protocol", 
            help = "Auth protocol used to talk to keystone", default='http')
        parser.add_argument("--keystone_auth_port", help = "Port of Keystone to talk to",
            default = '35357')
        parser.add_argument("--keystone_admin_token", 
            help = "admin_token value in keystone.conf")
        parser.add_argument("--keystone_insecure", 
            help = "Connect to keystone in secure or insecure mode if in https mode",
            default = 'False')

        parser.add_argument("--nworkers",
            help = "Number of worker processes for api and discovery services",
            default = '1')
        parser.add_argument("--haproxy", help = "Enable haproxy", action="store_true")
        parser.add_argument("--region_name", help = "The Region name for the openstack")
        parser.add_argument("--internal_vip", help = "VIP Address of openstack  nodes")
        parser.add_argument("--amqp_server_ip",
            help = "IP of the AMQP server to be used for neutron and api server")
        parser.add_argument("--manage_neutron", help = "Provision neutron user/role in Keystone.", default="yes")
  
        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncCfgm

def main(args_str = None):
    SetupVncCfgm(args_str)
#end main

if __name__ == "__main__":
    main() 
