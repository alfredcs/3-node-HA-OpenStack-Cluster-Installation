#!/usr/bin/python
#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Setup quantum confguration in keystone server
#

import os
import sys
import argparse
import ConfigParser

from fabric.api import run
from fabric.context_managers import settings

from keystoneclient.v2_0 import client
from keystoneclient import utils as ksutils
from keystoneclient import exceptions
import platform

class QuantumSetup(object):
    def __init__(self, args_str = None):

        # Parse arguments
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_quant_args(args_str)

        self._args_user = self._args.user
        self._args_passwd = self._args.password
        self._args_svc_passwd = self._args.svc_password
        self._args_region_name = self._args.region_name
        self._args_tenant_id = self._args.tenant
        self._args_quant_ip = self._args.quant_server_ip
        self._args_root_password = self._args.root_password
        self._args_quant_url = "http://%s:9696" % (self._args_quant_ip)

        self._args_ks_ip = self._args.ks_server_ip
        self._auth_url = "http://%s:35357/v2.0" % (self._args_ks_ip)
     

        # Flag to enable/disable quantum if needed
        # self._enable_quantum = True

        # some constants
        self._quant_tenant_name = "service"
        self._quant_svc_type = "network"
        if os.path.exists("/etc/neutron"):
            self._quant_svc_name = "neutron"
            self._quant_user_name = "neutron"
        else:
            self._quant_svc_name = "quantum"
            self._quant_user_name = "quantum"
        self._quant_admin_name = "admin"

        try:
            if self._args_svc_passwd:
                self.kshandle = client.Client(token=self._args_svc_passwd,
                                              endpoint=self._auth_url)
            else:
                self.kshandle = client.Client(username=self._args_user,
                                              password=self._args_passwd,
                                              tenant_name=self._args_tenant_id,
                                              auth_url=self._auth_url)
        except Exception as e:
            print e
            raise e

    # end __init__

    def _parse_quant_args(self, args_str):
        '''
        Eg. python quantum_server_setup.py -- ks_server_ip <ip-address> 
                 --quant_server_ip <ip-address> --tenant <id> --user <user>
                 --password <passwd> --svc_password <passwd>
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        keystone_server_defaults = {
            'ks_server_ip': '127.0.0.1',
            'quant_server_ip': '127.0.0.1',
            'tenant': 'admin',
            'user': 'admin',
            'password': 'contrail123',
            'svc_password': 'contrail123',
            'root_password': 'c0ntrail123',
            'region_name': 'RegionOne',
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            keystone_server_defaults.update(dict(config.items("GLOBAL")))

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

        all_defaults = { 'keystone': keystone_server_defaults }
        parser.set_defaults(**all_defaults)

        parser.add_argument("--ks_server_ip", help = "IP Address of quantum server")
        parser.add_argument("--quant_server_ip", help = "IP Address of quantum server")
        parser.add_argument("--tenant", help = "Tenant ID on keystone server")
        parser.add_argument("--user", help = "User ID to access keystone server")
        parser.add_argument("--password", help = "Password to access keystone server")
        parser.add_argument("--svc_password", help = "Quantum service password on keystone server")
        parser.add_argument("--root_password", help = "Root password for keystone server")
        parser.add_argument("--region_name", help = "Region Name for quantum endpoint")
    
        self._args = parser.parse_args(remaining_argv)

    # end _parse_quant_args

    def quant_set_tenant_id(self):
        # check if quantum tenant exists
        try:
            quant_tenant = self.kshandle.tenants.find(name=self._quant_tenant_name)
            if quant_tenant:
            # service tenant exists! return
                print "tenant %s exists!" % (self._quant_tenant_name)
                return quant_tenant.id
        except exceptions.NotFound as e:
            pass

        # tenant does not exist, create one
        try:
            quant_tenant = self.kshandle.tenants.create(tenant_name=self._quant_tenant_name,
                                                        description=self._quant_tenant_name,
                                                        enabled=True)
        except Exception as e:
            print e
            raise e

        return quant_tenant.id
    # end quant_set_tenant_id

    def quant_set_svc_id(self):
        # check if quantum service exists
        try:
            quant_svc = self.kshandle.services.find(name=self._quant_svc_name)
            if quant_svc:
                # service exists! return
                print "service %s exists!" % (self._quant_svc_name)
                return quant_svc.id
        except exceptions.NotFound as e:
            pass

        # service does not exist, create one
        try:
            quant_svc = self.kshandle.services.create(name=self._quant_svc_name,
                                                      service_type=self._quant_svc_type,
                                                      description=self._quant_svc_type)
        except Exception as e:
            raise e

        return quant_svc.id
    # end quant_set_svc_id

    def quant_set_user_id(self):
        # check if quantum service user exists
        try:
            quant_user = self.kshandle.users.find(name=self._quant_user_name)
            if quant_user:
                # user exists! return
                print "user %s exists! updating its password" % (self._quant_user_name)
                quant_user = self.kshandle.users.update_password(quant_user.id, self._args_svc_passwd)
                return quant_user.id
        except exceptions.NotFound as e:
            pass

        # users does not exist, create one
        try:
            quant_user = self.kshandle.users.create(name=self._quant_user_name,
                                                    password=self._args_svc_passwd,
                                                    email="%s@example.com" % (self._quant_user_name),
                                                    tenant_id=self.quant_tenant_id)
        except Exception as e:
            print e
            raise e

        return quant_user.id
    # end quant_set_user_id

    def quant_set_admin_role_id(self):
        # check if admin role exists
        try:
            quant_role = self.kshandle.roles.find(name=self._quant_admin_name)
            if quant_role:
                # admin role exists! return
                print "admin role exists!"
                return quant_role.id
        except exceptions.NotFound as e:
            pass

        # admin role does not exist, create one
        try:
            quant_role = self.kshandle.roles.create(name=self._quant_admin_name)
        except Exception as e:
            print e
            raise e

        return quant_role.id
    # end quant_set_admin_role_id

    def quant_set_user_admin_role(self):
        # check if role is already admin
        ks_uroles = self.kshandle.users.list_roles(self.quant_user_id, self.quant_tenant_id)
        if len(ks_uroles):
            quant_urole = [urole for urole in ks_uroles if urole.name == "admin"]
            if len(quant_urole):
                # role exists! return
                print "user role is already admin !"
                return

        # role admin does not exist, create one
        try:
            self.kshandle.roles.add_user_role(user=self.quant_user_id,
                                              role=self.admin_role_id,
                                              tenant=self.quant_tenant_id)
        except Exception as e:
            print e
            raise e

        return
    # end quant_set_user_admin_role

    def quant_set_endpoints(self):
        # check if endpoint exists
        try:
            quant_ends = self.kshandle.endpoints.find(service_id=self.quant_svc_id)
            if quant_ends:
                # service tenant exists! possible that the openstack node is setup independently
                # delete and recreate it
                print "Delete existing service endpoint and recreate."
                self.kshandle.endpoints.delete(quant_ends.id)
        except exceptions.NotFound as e:
            pass

        # service endpoint does not exist, create one
        try:
            self.kshandle.endpoints.create(region=self._args.region_name,
                                           service_id=self.quant_svc_id,
                                           publicurl=self._args_quant_url,
                                           adminurl=self._args_quant_url,
                                           internalurl=self._args_quant_url)
        except Exception as e:
            print e
            raise e

        return
    # end quant_set_endpoints

    def do_quant_setup(self):
        pdist = platform.dist()[0]
        # get service tenant ID
        self.quant_tenant_id = self.quant_set_tenant_id()

        # get quantum service ID
        self.quant_svc_id = self.quant_set_svc_id()

        # get quantum user ID
        self.quant_user_id = self.quant_set_user_id()

        # get admin role ID
        self.admin_role_id = self.quant_set_admin_role_id()

        # set quantum to admin role
        self.quant_set_user_admin_role()

        # Create quantum endpoints now
        self.quant_set_endpoints()

        if not os.path.exists("/etc/neutron"):
            #Fix the quantum url safely as openstack node may have been setup independently
            with settings(host_string='root@%s' %(self._args_ks_ip), password = self._args_root_password):
                run('openstack-config --set /etc/nova/nova.conf DEFAULT quantum_url %s' % self._args_quant_url)
                if pdist == 'Ubuntu': 
                    run('service keystone restart')
                    run('service nova-api restart')
                else:
                    run('service openstack-keystone restart')
                    run('service openstack-nova-api restart')

    # end do_quant_setup

# end class QuantumSetup

def main(args_str = None):
    quant_obj = QuantumSetup(args_str)
    quant_obj.do_quant_setup()
# end main

if __name__ == "__main__":
    main()
