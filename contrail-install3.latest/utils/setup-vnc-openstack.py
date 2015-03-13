#!/usr/bin/python
#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncOpenstack(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        self_ip = self._args.self_ip
        cfgm_ip = self._args.cfgm_ip
        keystone_ip = self._args.keystone_ip
        internal_vip = self._args.internal_vip
        contrail_internal_vip = self._args.contrail_internal_vip
        openstack_index = self._args.openstack_index
        openstack_ip_list = self._args.openstack_ip_list
        service_token = self._args.service_token
        ks_auth_protocol = self._args.keystone_auth_protocol
        amqp_server_ip = self._args.amqp_server_ip
        quantum_service_protocol = self._args.quantum_service_protocol

        setup_args_str = "--role openstack "
        setup_args_str = setup_args_str + " --openstack_ip %s " % (self_ip)
        if self._args.mgmt_self_ip:
            setup_args_str = setup_args_str + " --mgmt_self_ip %s " % (self._args.mgmt_self_ip)
        setup_args_str = setup_args_str + " --cfgm_ip %s " %(cfgm_ip)
        setup_args_str = setup_args_str + " --keystone_ip %s " %(keystone_ip)
        setup_args_str = setup_args_str + " --ks_auth_protocol %s" %(ks_auth_protocol)
        setup_args_str = setup_args_str + " --amqp_server_ip %s" %(amqp_server_ip)
        setup_args_str = setup_args_str + " --quantum_service_protocol %s" %(quantum_service_protocol)
        if internal_vip:
            setup_args_str = setup_args_str + " --internal_vip %s " %(internal_vip)
        if contrail_internal_vip:
            setup_args_str = setup_args_str + " --contrail_internal_vip %s " %(contrail_internal_vip)
        if service_token:
            setup_args_str = setup_args_str + " --service_token %s " %(service_token)
        if self._args.haproxy:
            setup_args_str = setup_args_str + " --haproxy"
        if openstack_index:
            setup_args_str = setup_args_str + " --openstack_index %s" \
                                 %(self._args.openstack_index)
        if openstack_ip_list:
            setup_args_str = setup_args_str + " --openstack_ip_list %s"  % (' '.join(openstack_ip_list))
        
        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-openstack.py --self_ip 10.1.5.11 --cfgm_ip 10.1.5.12
                   --keystone_ip 10.1.5.13 --service_token c0ntrail123 --haproxy
                   --internal_vip 10.1.5.100 --openstack_index 1
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'self_ip': '127.0.0.1',
            'service_token': '',
            'cfgm_ip': '127.0.0.1',
            'keystone_ip': '127.0.0.1',
            'haproxy': False,
            'ks_auth_protocol':'http',
            'amqp_server_ip':'127.0.0.1',
            'quantum_service_protocol': 'http',
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
        parser.add_argument("--mgmt_self_ip", help = "Management IP Address of this system")
        parser.add_argument("--cfgm_ip", help = "IP Address of quantum node")
        parser.add_argument("--keystone_ip", help = "IP Address of keystone node")
        parser.add_argument("--internal_vip", help = "VIP Address of openstack  nodes")
        parser.add_argument("--contrail_internal_vip", help = "VIP Address of config  nodes")
        parser.add_argument("--service_token", help = "The service password to access keystone")
        parser.add_argument("--haproxy", help = "Enable haproxy", action="store_true")
        parser.add_argument("--quantum_service_protocol", 
            help = "Protocol of neutron for nova to use", default="http")
        parser.add_argument("--amqp_server_ip", 
            help = "IP of the AMQP server to be used for openstack")
        parser.add_argument("--keystone_auth_protocol",
            help = "Auth protocol used to talk to keystone", default='http')
        parser.add_argument("--openstack_index", help = "The index of this openstack node")
        parser.add_argument("--openstack_ip_list", help = "List of IP Addresses of openstack servers",
                            nargs='+', type=str)

        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncOpenstack

def main(args_str = None):
    SetupVncOpenstack(args_str)
#end main

if __name__ == "__main__":
    main() 
