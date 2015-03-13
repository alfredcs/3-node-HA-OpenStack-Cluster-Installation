#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncVrouter(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        cfgm_ip = self._args.cfgm_ip
        keystone_ip = self._args.keystone_ip
        internal_vip = self._args.internal_vip
        external_vip = self._args.external_vip
        contrail_internal_vip = self._args.contrail_internal_vip
        service_token = self._args.service_token
        ncontrols = self._args.ncontrols
        non_mgmt_ip = self._args.non_mgmt_ip
        non_mgmt_gw = self._args.non_mgmt_gw
        vgw_public_subnet = self._args.public_subnet
        vgw_public_vn_name = self._args.public_vn_name
        vgw_intf_list = self._args.vgw_intf
        vgw_gateway_routes = self._args.gateway_routes
        ks_auth_protocol = self._args.keystone_auth_protocol
        ks_auth_port = self._args.keystone_auth_port
        amqp_server_ip = self._args.amqp_server_ip
        amqp_server_ip_list = self._args.amqp_server_ip_list
        quantum_service_protocol = self._args.quantum_service_protocol
        if not self._args.openstack_mgmt_ip :
            openstack_mgmt_ip = keystone_ip
        else:
            openstack_mgmt_ip = self._args.openstack_mgmt_ip
        if self._args.vmware :
            vmware_ip = self._args.vmware
            vmware_username = self._args.vmware_username
            vmware_passwd = self._args.vmware_passwd
            vmware_vmpg_vswitch = self._args.vmware_vmpg_vswitch


        setup_args_str = "--role compute --compute_ip %s " %(self._args.self_ip)
        if self._args.mgmt_self_ip:
            setup_args_str = setup_args_str + " --mgmt_self_ip %s " % (self._args.mgmt_self_ip)
        setup_args_str = setup_args_str + " --cfgm_ip %s " %(cfgm_ip)
        setup_args_str = setup_args_str + " --keystone_ip %s " %(keystone_ip)
        setup_args_str = setup_args_str + " --openstack_mgmt_ip %s " %(openstack_mgmt_ip)
        setup_args_str = setup_args_str + " --ks_auth_protocol %s" %(ks_auth_protocol)
        setup_args_str = setup_args_str + " --ks_auth_port %s" %(ks_auth_port)
        setup_args_str = setup_args_str + " --amqp_server_ip %s" %(amqp_server_ip)
        if amqp_server_ip_list:
            setup_args_str = setup_args_str + " --amqp_server_ip_list %s" %(' '. join(amqp_server_ip_list))
        setup_args_str = setup_args_str + " --quantum_service_protocol %s" %(quantum_service_protocol)
        
        if service_token:
            setup_args_str = setup_args_str + " --service_token %s " %(service_token)
        ncontrols = 2
        setup_args_str = setup_args_str + " --ncontrols %s " %(ncontrols)
        if non_mgmt_ip: 
            setup_args_str = setup_args_str + " --non_mgmt_ip %s " %(non_mgmt_ip)
            setup_args_str = setup_args_str + " --non_mgmt_gw %s " %(non_mgmt_gw)
        if vgw_public_subnet and  vgw_public_vn_name:
            setup_args_str = setup_args_str + " --vgw_public_subnet %s " %(vgw_public_subnet)
            setup_args_str = setup_args_str + " --vgw_public_vn_name %s " %(vgw_public_vn_name)
            setup_args_str = setup_args_str + " --vgw_intf_list %s " %(vgw_intf_list)
            if vgw_gateway_routes:
                setup_args_str = setup_args_str + " --vgw_gateway_routes %s " %(vgw_gateway_routes)
        if self._args.haproxy:
            setup_args_str = setup_args_str + " --haproxy"
        if self._args.vmware:
            setup_args_str = setup_args_str + " --vmware %s --vmware_username %s --vmware_passwd %s --vmware_vmpg_vswitch %s" %(vmware_ip, vmware_username, vmware_passwd, vmware_vmpg_vswitch)

        if internal_vip:
            setup_args_str = setup_args_str + " --internal_vip %s " %(internal_vip)
        if external_vip:
            setup_args_str = setup_args_str + " --external_vip %s " %(external_vip)
        if contrail_internal_vip:
            setup_args_str = setup_args_str + " --contrail_internal_vip %s " %(contrail_internal_vip)
        if self._args.no_contrail_openstack:
            setup_args_str = setup_args_str + " --no_contrail_openstack"

        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-vrouter.py --cfgm_ip 10.1.5.11 --keystone_ip 10.1.5.12
                   --self_ip 10.1.5.12 --service_token 'c0ntrail123' --ncontrols 1
                   --haproxy --internal_vip 10.1.5.200
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'cfgm_ip': '127.0.0.1',
            'keystone_ip': '127.0.0.1',
            'openstack_mgmt_ip': None,
            'service_token': '',
            'self_ip': '127.0.0.1',
            'ncontrols': '2',
            'non_mgmt_ip': None,
            'non_mgmt_gw': None,
            'public_subnet': None,
            'public_vn_name': None,
            'vgw_intf': None,
            'gateway_routes': None,
            '': None,
            'haproxy': False,
            'ks_auth_protocol':'http',
            'ks_auth_port':'35357',
            'amqp_server_ip':'127.0.0.1',
            'amqp_server_ip_list':'127.0.0.1',
            'quantum_service_protocol':'http',
            'vmware': None,
            'vmware_username': 'root',
            'vmware_passwd': 'c0ntrail123',
            'vmware_vmpg_vswitch': 'c0ntrail123',
            'no_contrail_openstack': False,
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

        parser.add_argument("--cfgm_ip", help = "IP Address of the config node")
        parser.add_argument("--keystone_ip", help = "IP Address of the keystone node")
        parser.add_argument("--openstack_mgmt_ip", help = "Mgmt IP Address of the openstack node if it is different from openstack_IP")
        parser.add_argument("--service_token", help = "The service password to access keystone")
        parser.add_argument("--self_ip", help = "IP Address of this(compute) node")
        parser.add_argument("--mgmt_self_ip", help = "Management IP Address of this system")
        parser.add_argument("--ncontrols", help = "Number of control-nodes in the system")
        parser.add_argument("--non_mgmt_ip", help = "IP Address of non-management interface(fabric network) on the compute  node")
        parser.add_argument("--non_mgmt_gw", help = "Gateway Address of the non-management interface(fabric network) on the compute node")
        parser.add_argument("--public_subnet", help = "Subnet of the virtual network used for public access")
        parser.add_argument("--vgw_intf", help = "Virtual gateway intreface name")
        parser.add_argument("--public_vn_name", help = "Fully-qualified domain name (FQDN) of the routing-instance that needs public access")
        parser.add_argument("--gateway_routes", help = "List of route need to be added in agent configuration for virtual gateway")
        parser.add_argument("--haproxy", help = "Enable haproxy", action="store_true")
        parser.add_argument("--keystone_auth_protocol",
            help = "Auth protocol used to talk to keystone", default='http')
        parser.add_argument("--keystone_auth_port", help = "Port of Keystone to talk to",default='35357')
        parser.add_argument("--quantum_service_protocol", help = "Protocol of neutron for nova to use",
            default = 'http')
        parser.add_argument("--amqp_server_ip", help = "IP of the AMQP server to be used for openstack")
        parser.add_argument("--amqp_server_ip_list", help = "IP of the AMQP server to be used for openstack",
                            nargs='+', type=str)
        parser.add_argument("--vmware", help = "The Vmware ESXI IP")
        parser.add_argument("--vmware_username", help = "The Vmware ESXI username")
        parser.add_argument("--vmware_passwd", help = "The Vmware ESXI password")
        parser.add_argument("--vmware_vmpg_vswitch", help = "The Vmware VMPG vswitch name")
        parser.add_argument("--internal_vip", help = "Internal VIP Address of openstack nodes")
        parser.add_argument("--external_vip", help = "External VIP Address of openstack nodes")
        parser.add_argument("--contrail_internal_vip", help = "VIP Address of config  nodes")
        parser.add_argument("--no_contrail_openstack", help = "Do not provision contrail Openstack in compute node.", action="store_true")

        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncVrouter

def main(args_str = None):
    SetupVncVrouter(args_str)
#end main

if __name__ == "__main__":
   main() 
