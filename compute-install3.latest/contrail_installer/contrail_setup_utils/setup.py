import argparse
import ConfigParser

import platform
import os
import sys
import time
import re
import string
import socket
import netifaces, netaddr
import subprocess
import fnmatch
import struct
import shutil
import json
from pprint import pformat
import xml.etree.ElementTree as ET
import platform

#dist = platform.dist()[0]
#if  dist == 'centos':
#    _tgt_path = os.path.abspath(os.path.dirname(sys.argv[0]))
#    subprocess.call("sudo pip-python install %s/contrail_setup_utils/pycrypto-2.6.tar.gz" %(_tgt_path), shell=True)
#    subprocess.call("sudo pip-python install %s/contrail_setup_utils/paramiko-1.11.0.tar.gz" %(_tgt_path), shell=True)
#    subprocess.call("sudo pip-python install %s/contrail_setup_utils/Fabric-1.7.0.tar.gz" %(_tgt_path), shell=True)
#    subprocess.call("sudo pip-python install %s/contrail_setup_utils/zope.interface-3.7.0.tar.gz" %(_tgt_path), shell=True)

import tempfile
from fabric.api import local, env, run
from fabric.operations import get, put
from fabric.context_managers import lcd, settings, hide
from fabric.api import local, env, run
from fabric.operations import get, put
from fabric.context_managers import lcd, settings

# Get Environment Stuff
env.password='c0ntrail123'
if os.getenv('PASSWORD') :
    env.password=os.getenv('PASSWORD')

env.admin_username='admin'
if os.getenv('ADMIN_USERNAME') :
    env.admin_username=os.getenv('ADMIN_USERNAME')

env.admin_token='contrail123'
if os.getenv('ADMIN_TOKEN') :
    env.admin_token=os.getenv('ADMIN_TOKEN')

env.admin_tenant ='admin'
if os.getenv('ADMIN_TENANT') :
    env.admin_tenant=os.getenv('ADMIN_TENANT')

# TODO following keystone credentials hardcoded
ks_admin_user = env.admin_username
ks_admin_password = env.admin_token
ks_admin_tenant_name = env.admin_tenant
contrail_bin_dir = '/opt/contrail/bin'

from contrail_config_templates import api_server_conf_template
from contrail_config_templates import quantum_conf_template
from contrail_config_templates import schema_transformer_conf_template
from contrail_config_templates import svc_monitor_conf_template
from contrail_config_templates import bgp_param_template
from contrail_config_templates import dns_param_template
from contrail_config_templates import vnswad_conf_template
from contrail_config_templates import discovery_conf_template
from contrail_config_templates import vizd_param_template
from contrail_config_templates import qe_param_template
from contrail_config_templates import opserver_param_template
from contrail_config_templates import vnc_api_lib_ini_template
from contrail_config_templates import agent_param_template
from contrail_config_templates import contrail_api_ini_template
from contrail_config_templates import contrail_api_ini_centos_template
from contrail_config_templates import contrail_api_svc_template
from contrail_config_templates import contrail_discovery_ini_template
from contrail_config_templates import contrail_discovery_ini_centos_template
from contrail_config_templates import contrail_discovery_svc_template
from contrail_config_templates import database_nodemgr_param_template
from contrail_config_templates import contrail_nodemgr_database_template
from contrail_config_templates import ifmap_ifmap_template
from contrail_config_templates import ifmap_basicauthusers_template
from contrail_config_templates import ifmap_authorization_template
from contrail_config_templates import ifmap_publisher_template
from contrail_config_templates import ifmap_log4j_template
from contrail_config_templates import keepalived_conf_template
from contrail_config_templates import galera_param_template
from contrail_config_templates import cmon_param_template
from contrail_config_templates import cmon_conf_template
from contrail_config_templates import wsrep_conf_template
from contrail_config_templates import wsrep_conf_centos_template

CONTRAIL_FEDORA_TEMPL = string.Template("""
[contrail_fedora_repo]
name=Contrail Fedora Repo
baseurl=file://$__contrail_fedora_path__
enabled=1
gpgcheck=0
""")

CONTRAIL_DEMO_TEMPL = string.Template("""
[contrail_demo_repo]
name=Contrail Demo Repo
baseurl=file://$__contrail_demo_path__
enabled=1
gpgcheck=0
""")

CASSANDRA_CONF = '/etc/cassandra/conf'
CASSANDRA_CONF_FILE = 'cassandra.yaml'
CASSANDRA_ENV_FILE = 'cassandra-env.sh'

class ExtList (list):
    def findex (self, fun):
        for i, x in enumerate (self):
            if fun (x):
                return i
        raise LookupError, 'No matching element in list'


class Setup(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        self._setup_tgt_path = os.path.abspath(os.path.dirname(sys.argv[0]))

        self._temp_dir_name = tempfile.mkdtemp()
        self._fixed_qemu_conf = False
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup.py --role config --role control --cfgm_ip 127.0.0.1
            [--use_certs [--puppet_server <fqdn>]] [--multi_tenancy]
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'use_certs': False,
            'puppet_server': None,
        }
        cfgm_defaults = {
            'cfgm_ip': '127.0.0.1',
            'keystone_ip': '127.0.0.1',
            'service_token': '',
            'n_api_workers': '1',
            'multi_tenancy': False,
            'haproxy': False,
            'region_name': None,
            'ks_auth_protocol':'http',
            'ks_auth_port':'35357',
            'ks_insecure':'False',
            'amqp_server_ip': '127.0.0.1',
            'manage_neutron' : True,
            'contrail_internal_vip' : None,
        }
        openstack_defaults = {
            'cfgm_ip': '127.0.0.1',
            'service_token': '',
            'haproxy': False,
            'ks_auth_protocol':'http',
            'amqp_server_ip': '127.0.0.1',
            'quantum_service_protocol':'http',
            'mgmt_self_ip' : None,
            'internal_vip' : None,
            'external_vip' : None,
        }
        control_node_defaults = {
            'cfgm_ip': '127.0.0.1',
            'collector_ip': '127.0.0.1',
            'control_ip': '127.0.0.1',
        }
        compute_node_defaults = {
            'compute_ip': '127.0.0.1',
            'keystone_ip': '127.0.0.1',
            'ks_auth_protocol':'http',
            'service_token': '',
            'haproxy': False,
            'ncontrols' : 2,
            'physical_interface': None,
            'non_mgmt_ip': None,
            'non_mgmt_gw': None,
            'vgw_public_subnet': None,
            'vgw_public_vn_name': None,
            'vgw_intf_list': None,
            'vgw_gateway_routes': None,
            'amqp_server_ip': '127.0.0.1',
            'amqp_server_ip_list': '127.0.0.1',
            'quantum_service_protocol': 'http',
            'no_contrail_openstack' : False
        }
        collector_defaults = {
            'cfgm_ip': '127.0.0.1',
            'self_collector_ip': '127.0.0.1',
        }
        database_defaults = {
            'database_dir' : '/usr/share/cassandra',
            'database_listen_ip' : '127.0.0.1',                     
	    'cfgm_ip': '127.0.0.1',
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            global_defaults.update(dict(config.items("GLOBAL")))
            cfgm_defaults.update(dict(config.items("CFGM")))
            openstack_defaults.update(dict(config.items("OPENSTACK")))
            control_node_defaults.update(dict(config.items("CONTROL-NODE")))
            compute_node_defaults.update(dict(config.items("COMPUTE-NODE")))
            collector_defaults.update(dict(config.items("COLLECTOR")))
            database_defaults.update(dict(config.items("DATABASE")))

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

        all_defaults = {'global': global_defaults,
                        'cfgm': cfgm_defaults,
                        'openstack': openstack_defaults,
                        'control-node': control_node_defaults,
                        'compute-node': compute_node_defaults,
                        'collector': collector_defaults,
                        'database': database_defaults,
                       }
        parser.set_defaults(**all_defaults)

        parser.add_argument("--role", action = 'append', 
                            help = "Role of server (config, openstack, control, compute, collector, webui, database")
        parser.add_argument("--cfgm_ip", help = "IP Address of Configuration Node")
        parser.add_argument("--mgmt_self_ip", help = "Managment IP Address of any Node")
        parser.add_argument("--openstack_ip", help = "IP Address of Openstack Node")
        parser.add_argument("--internal_vip", help = "Internal VIP Address of HA Openstack Nodes")
        parser.add_argument("--external_vip", help = "External VIP Address of HA Openstack Nodes")
        parser.add_argument("--contrail_internal_vip", help = "Internal VIP Address of HA config Nodes")
        parser.add_argument("--keystone_ip", help = "IP Address of Keystone Node")
        parser.add_argument("--openstack_mgmt_ip", help = "Management IP Address of Openstack Node")
        parser.add_argument("--collector_ip", help = "IP Address of Collector Node")
        parser.add_argument("--discovery_ip", help = "IP Address of Discovery Node")
        parser.add_argument("--control_ip", help = "IP Address of first Control Node (for control role)")
        parser.add_argument("--ncontrols", help = "Number of Control Nodes in the system (for compute role)")
        parser.add_argument("--compute_ip", help = "IP Address of Compute Node (for compute role)")
        parser.add_argument("--service_token", help = "The service password to access keystone")
        parser.add_argument("--region_name", help = "The Region Name in Openstack")
        parser.add_argument("--haproxy", help = "Enable haproxy", action="store_true")
        parser.add_argument("--no_contrail_openstack", help = "Do not provision contrail Openstack in compute node", action="store_true")
        parser.add_argument("--manage_neutron", help = "Provision neutron in Keystone", action="store_true")
        parser.add_argument("--physical_interface", help = "Name of the physical interface to use")
        parser.add_argument("--non_mgmt_ip", help = "IP Address of non-management interface(fabric network) on the compute  node")
        parser.add_argument("--non_mgmt_gw", help = "Gateway Address of the non-management interface(fabric network) on the compute node")
        parser.add_argument("--use_certs", help = "Use certificates for authentication",
            action="store_true")
        parser.add_argument("--vgw_public_subnet", help = "Subnet of the virtual network used for public access")
        parser.add_argument("--vgw_public_vn_name", help = "Fully-qualified domain name (FQDN) of the routing-instance that needs public access")
        parser.add_argument("--vgw_intf_list", help = "List of virtual getway intreface")
        parser.add_argument("--vgw_gateway_routes", help = "Static route to be configured in agent configuration for VGW")
        parser.add_argument("--ks_auth_protocol", help = "Protocol to use while talking to Keystone")
        parser.add_argument("--ks_auth_port", help = "Port to use while talking to Keystone",default='35357')
        parser.add_argument("--ks_admin_token", help = "Admin token to be used while talking to keystone",)
        parser.add_argument("--ks_insecure", help = "Option to connect to keystone in secure/insecure mode when using https")
        parser.add_argument("--quantum_service_protocol", help = "Protocol of quantum/neutron for nova to use ", default='http')
        parser.add_argument("--amqp_server_ip", help = "IP of the AMQP Server used to configure openstack components",)
        parser.add_argument("--amqp_server_ip_list", help = "IP list of the AMQP Server used to configure openstack components", 
                            nargs = '+', type = str)
        parser.add_argument("--puppet_server", help = "FQDN of Puppet Master")
        parser.add_argument("--multi_tenancy", help = "Enforce resource permissions (implies keystone token validation)",
            action="store_true")
        parser.add_argument("--cassandra_ip_list", help = "IP Addresses of Cassandra Nodes", nargs = '+', type = str)
        parser.add_argument("--zookeeper_ip_list", help = "IP Addresses of Zookeeper servers", nargs = '+', type = str)
        parser.add_argument("--database_index", help = "Index of this database node")
        parser.add_argument("--galera_ip_list", help = "IP Addresses of Galera servers", nargs = '+', type = str)
        parser.add_argument("--openstack_ip_list", help = "IP Addresses of openstack Servers", nargs = '+', type = str)
        parser.add_argument("--openstack_index", help = "Index of this openstack node", type = int)
        parser.add_argument("--cfgm_index", help = "Index of this cfgm node", type = int)
        parser.add_argument("--num_nodes", help = "Number of available nodes", type = int)
        parser.add_argument("--quantum_port", help = "Quantum server port", default='9696')
        parser.add_argument("--n_api_workers",
            help="Number of API/discovery worker processes to be launched",
            default='1')
        parser.add_argument("--database_listen_ip", help = "Listen IP Address of database node", default = '127.0.0.1')
        pdist = platform.dist()[0]
        if pdist == 'fedora' or pdist == 'centos' or pdist == 'redhat':
            parser.add_argument("--database_dir", help = "Directory where database binary exists", default = '/usr/share/cassandra')
        if pdist == 'Ubuntu':
            parser.add_argument("--database_dir", help = "Directory where database binary exists", default = '/etc/cassandra')
        parser.add_argument("--data_dir", help = "Directory where database stores data")
        parser.add_argument("--analytics_data_dir", help = "Directory where database stores data")
        parser.add_argument("--ssd_data_dir", help = "Directory where database stores data")
        parser.add_argument("--database_initial_token", help = "Initial token for database node")
        parser.add_argument("--database_seed_list", help = "List of seed nodes for database", nargs='+')
        parser.add_argument("--num_collector_nodes", help = "Number of Collector Nodes", type = int)
        parser.add_argument("--self_collector_ip", help = "Self IP of Collector Node")
        parser.add_argument("--analytics_data_ttl", help = "TTL in hours of analytics data stored in database", type = int, default = 24 * 2)
        parser.add_argument("--analytics_syslog_port", help = "Listen port for analytics syslog server", type = int, default = -1)
        parser.add_argument("--storage-master", help = "IP Address of storage master node")
        parser.add_argument("--storage-hostnames", help = "Host names of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-hosts", help = "IP Addresses of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-host-tokens", help = "Passwords of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-disk-config", help = "Disk list to be used for distributed storage", nargs="+", type=str)
        parser.add_argument("--storage-ssd-disk-config", help = "SSD Disk list to be used for distributed storage", nargs="+", type=str)
        parser.add_argument("--storage-local-disk-config", help = "Disk list to be used for local storage", nargs="+", type=str)
        parser.add_argument("--storage-local-ssd-disk-config", help = "SSD Disk list to be used for local storage", nargs="+", type=str)
        parser.add_argument("--storage-nfs-disk-config", help = "Disk list to be used for local storage", nargs="+", type=str)
        parser.add_argument("--storage-journal-config", help = "Disk list to be used for distributed storage journal", nargs="+", type=str)
        parser.add_argument("--storage-directory-config", help = "Directories to be sued for distributed storage", nargs="+", type=str)
        parser.add_argument("--live-migration", help = "Live migration enabled")
        parser.add_argument("--nfs-live-migration", help = "NFS for Live migration enabled")
        parser.add_argument("--nfs-livem-subnet", help = "Subnet for NFS for Live migration VM", nargs="+", type=str)
        parser.add_argument("--nfs-livem-image", help = "Image for NFS for Live migration VM", nargs="+", type=str)
        parser.add_argument("--nfs-livem-host", help = "Image for NFS for Live migration VM", nargs="+", type=str)
        parser.add_argument("--add-storage-node", help = "Dynamic addition of storage node")
        parser.add_argument("--storage-setup-mode", help = "Storage configuration mode")
        parser.add_argument("--vmware", help = "Vmware ESXI IP", type=str)
        parser.add_argument("--vmware_username", help = "Vmware ESXI Username", type=str)
        parser.add_argument("--vmware_passwd", help = "Vmware ESXI Password", type=str)
        parser.add_argument("--vmware_vmpg_vswitch", help = "Vmware VMPG vswitch name", type=str)

    
        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

    def _template_substitute(self, template, vals):
        data = template.safe_substitute(vals)
        return data
    #end _template_substitute

    def _template_substitute_write(self, template, vals, filename):
        data = self._template_substitute(template, vals)
        outfile = open(filename, 'w')
        outfile.write(data)
        outfile.close()
    #end _template_substitute_write

    def _replaces_in_file(self, file, replacement_list):
        rs = [ (re.compile(regexp), repl) for (regexp, repl) in replacement_list]
        file_tmp = file + ".tmp"
        with open(file, 'r') as f:
            with open(file_tmp, 'w') as f_tmp:
                for line in f:
                    for r, replace in rs:
                        match = r.search(line)
                        if match:
                            line = replace + "\n"
                    f_tmp.write(line)
        shutil.move(file_tmp, file)
    #end _replaces_in_file

    def replace_in_file(self, file, regexp, replace):
        self._replaces_in_file(file, [(regexp, replace)])
    #end replace_in_file    
        
    def setup_crashkernel_params(self):
        local(r"sed -i 's/crashkernel=.*\([ | \"]\)/crashkernel=384M-2G:64M,2G-16G:128M,16G-:256M\1/g' /etc/grub.d/10_linux")
        local("update-grub")

    def enable_kernel_core (self):
        '''
            enable_kernel_core:
                update grub file
                install grub2
                enable services
        '''
        gcnf = ''
        with open ('/etc/default/grub', 'r') as f:
            gcnf = f.read ()
            p = re.compile ('\s*GRUB_CMDLINE_LINUX')
            el = ExtList (gcnf.split ('\n'))
            try:
                i = el.findex (p.match)
                exec (el[i])
                el[i] = 'GRUB_CMDLINE_LINUX="%s crashkernel=128M"' % (
                        ' '.join (filter (lambda x: not x.startswith (
                                    'crashkernel='), GRUB_CMDLINE_LINUX.split ())))
                exec (el[i])
                el[i] = 'GRUB_CMDLINE_LINUX="%s kvm-intel.nested=1"' % (
                        ' '.join (filter (lambda x: not x.startswith (
                                    'kvm-intel.nested='), GRUB_CMDLINE_LINUX.split ())))

                with open ('%s/grub' % self._temp_dir_name, 'w') as f:
                    f.write ('\n'.join (el))
                    f.flush ()
                local ('sudo mv %s/grub /etc/default/grub' % (self._temp_dir_name))
                local ('sudo /usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg')
                if 'compute' in self._args.role :
                    local ('for s in abrt-vmcore abrtd kdump; do chkconfig ${s} on; done')
            except LookupError:
                print 'Improper grub file, kernel crash not enabled'
    #end enable_kernel_core

    def setup_repo(self):

        with lcd("/etc/yum.repos.d/"):
            ls_out = local("find . -maxdepth 1 -type f -name '*'", capture = True)
            existing_repos = [ repo for repo in ls_out.split() if not re.match('./contrail*', repo) ]

            if existing_repos:
                with settings(warn_only = True):
                    local("sudo mkdir saved-repos")
            for repo in existing_repos:
                if repo == 'saved-repos':
                    continue
                local("sudo mv %s saved-repos" %(repo))

            self._template_substitute_write(CONTRAIL_FEDORA_TEMPL,
                 {'__contrail_fedora_path__': self._setup_tgt_path},
                 '%s/contrail_fedora.repo' %(self._temp_dir_name))
            self._template_substitute_write(CONTRAIL_DEMO_TEMPL,
                 {'__contrail_demo_path__': self._setup_tgt_path},
                 '%s/contrail_demo.repo' %(self._temp_dir_name))
            local("sudo mv %s/contrail_fedora.repo ." %(self._temp_dir_name))
            local("sudo mv %s/contrail_demo.repo ." %(self._temp_dir_name))

        with lcd("%s" %(self._setup_tgt_path)):
            local("sudo createrepo .")

    #end setup_repo

    def install_packages(self):
        local("sudo yum clean all")

        if 'config' in self._args.role:
            local("sudo yum -y install openstack-quantum contrail-config openstack-quantum-contrail mysql qpid-cpp-server mysql-server")

        if 'openstack' in self._args.role:
            local("sudo yum -y install openstack-nova openstack-cinder openstack-glance openstack-keystone mysql qpid-cpp-server openstack_dashboard mysql-server")

        if 'control' in self._args.role:
            local("sudo yum -y install contrail-control")

        if 'collector' in self._args.role:
            local("sudo yum -y install contrail-analytics")

        if 'compute' in self._args.role :
            local("sudo yum -y install contrail-vrouter openstack-utils openstack-nova-compute")

    #end install_packages

    # Customized for Workday 
    # updated function to get the gateway based on FLAG
    def find_gateway (self, dev):
        gateway = ''
        gateway = local("netstat -rn | grep \"0.0.0.0\" | grep UG | grep %s | awk '{ print $2 }'" % dev,
                capture = True).strip()
        return gateway

    #end find_gateway

    def get_dns_servers (self, dev):
        dns_list = local("grep \"^nameserver\\>\" /etc/resolv.conf | awk  '{print $2}'",
                capture = True)
        return dns_list.split()
    #end get_dns_servers

    def get_domain_search_list (self):
        domain_list = ''
        domain_list = local("grep ^\"search\" /etc/resolv.conf | awk '{$1=\"\";print $0}'", capture = True).strip()
        if not domain_list:
            domain_list = local("grep ^\"domain\" /etc/resolv.conf | awk '{$1=\"\"; print $0}'", capture = True).strip()
        return domain_list

    def get_if_mtu (self, dev):
        mtu = local("ifconfig %s | grep mtu | awk '{ print $NF }'" % dev,
                capture = True).strip ()
        if not mtu:
            # for debian
            mtu = local(
              r"ifconfig %s | grep MTU | sed 's/.*MTU.\([0-9]\+\).*/\1/g'" % dev,
                capture = True).strip ()
        if mtu and mtu != '1500': return mtu
        return ''
    #end if_mtu

    def get_device_by_ip (self, ip):
        for i in netifaces.interfaces ():
            try:
                if i == 'pkt1':
                    continue
                if netifaces.ifaddresses (i).has_key (netifaces.AF_INET):
                    if ip == netifaces.ifaddresses (i)[netifaces.AF_INET][0][
                            'addr']:
                        if i == 'vhost0':
                             print "vhost0 is already present!"
    #                        raise RuntimeError, 'vhost0 already running with %s'%ip
                        return i
            except ValueError,e:
                print "Skipping interface %s" % i
        raise RuntimeError, '%s not configured, rerun w/ --physical_interface' % ip
    #end get_device_by_ip
    def get_secondary_device(self, primary):
        for i in netifaces.interfaces ():
            try:
                if i == 'pkt1':
                    continue
                if i == primary:
                    continue
                if i == 'vhost0':
                    continue
                if not netifaces.ifaddresses (i).has_key (netifaces.AF_INET):
                    return i
            except ValueError,e:
                print "Skipping interface %s" % i
        raise RuntimeError, '%s not configured, rerun w/ --physical_interface' % ip
    #end get_secondary_device

    
    def _is_string_in_file(self, string, filename):
        f_lines=[]
        if os.path.isfile( filename ):
            fd=open(ifcfg_file)
            f_lines=fd.readlines()
            fd.close()
        #end if  
        found= False
        for line in f_lines:
            if string in line:
                found= True
        return found
    #end _is_string_in_file
    
    def _rewrite_ifcfg_file(self, filename, dev, prsv_cfg):
        bond = False
        mac = ''
        temp_dir_name = self._temp_dir_name

        vlan = False
        if os.path.isfile ('/proc/net/vlan/%s' % dev):
            vlan_info = open('/proc/net/vlan/config').readlines()
            match = re.search('^%s.*\|\s+(\S+)$'%dev, "\n".join(vlan_info), flags=re.M|re.I)
            if not match:
                raise RuntimeError, 'Configured vlan %s is not found in /proc/net/vlan/config'%dev
            phydev = match.group(1)
            vlan = True

        if os.path.isdir ('/sys/class/net/%s/bonding' % dev):
            bond = True
        # end if os.path.isdir...

        mac = netifaces.ifaddresses(dev)[netifaces.AF_LINK][0]['addr']
        ifcfg_file='/etc/sysconfig/network-scripts/ifcfg-%s' %(dev)
        if not os.path.isfile( ifcfg_file ):
            ifcfg_file = temp_dir_name + 'ifcfg-' + dev
            with open (ifcfg_file, 'w') as f:
                f.write ('''#Contrail %s
TYPE=Ethernet
ONBOOT=yes
DEVICE="%s"
USERCTL=yes
NM_CONTROLLED=no
HWADDR=%s
''' % (dev, dev, mac))
                for dcfg in prsv_cfg:
                    f.write(dcfg+'\n')
                if vlan:
                    f.write('VLAN=yes\n')
        fd=open(ifcfg_file)
        f_lines=fd.readlines()
        fd.close()
        local("sudo rm -f %s" %ifcfg_file)
        new_f_lines=[]
        remove_items=['IPADDR', 'NETMASK', 'PREFIX', 'GATEWAY', 'HWADDR',
                      'DNS1', 'DNS2', 'BOOTPROTO', 'NM_CONTROLLED', '#Contrail']

        remove_items.append('DEVICE')
        new_f_lines.append('#Contrail %s\n' % dev)
        new_f_lines.append('DEVICE=%s\n' % dev)


        for line in f_lines:
            found=False
            for text in remove_items:
                if text in line:
                    found=True
            if not found:
                new_f_lines.append(line)

        new_f_lines.append('NM_CONTROLLED=no\n')
        if bond:
            new_f_lines.append('SUBCHANNELS=1,2,3\n')
        else:
            new_f_lines.append('HWADDR=%s\n' % mac)

        fdw=open(filename,'w')
        fdw.writelines(new_f_lines)
        fdw.close()

    def migrate_routes(self, device):
        '''
        Sample output of /proc/net/route :
        Iface   Destination     Gateway         Flags   RefCnt  Use     Metric  Mask            MTU     Window  IRTT
        p4p1    00000000        FED8CC0A        0003    0       0       0       00000000        0       0       0
        '''
        temp_dir_name = self._temp_dir_name
        cfg_file = '/etc/sysconfig/network-scripts/route-vhost0'
        tmp_file = '%s/route-vhost0'%(temp_dir_name)
        with open(tmp_file, 'w') as route_cfg_file:
            for route in open('/proc/net/route', 'r').readlines():
                if route.startswith(device):
                    route_fields = route.split()
                    destination = int(route_fields[1], 16)
                    gateway = int(route_fields[2], 16)
                    flags = int(route_fields[3], 16)
                    mask = int(route_fields[7], 16)
                    if flags & 0x2:
                        if destination != 0:
                            route_cfg_file.write(socket.inet_ntoa(struct.pack('I', destination)))
                            route_cfg_file.write('/' + str(bin(mask).count('1')) + ' ')
                            route_cfg_file.write('via ')
                            route_cfg_file.write(socket.inet_ntoa(struct.pack('I', gateway)) + ' ')
                            route_cfg_file.write('dev vhost0')
                        #end if detination...
                    #end if flags &...
                #end if route.startswith...
            #end for route...
        #end with open...
        local("sudo mv -f %s %s" %(tmp_file, cfg_file))
        #delete the route-dev file
        if os.path.isfile('/etc/sysconfig/network-scripts/route-%s'%device):
            os.unlink('/etc/sysconfig/network-scripts/route-%s'%device)
    #end def migrate_routes

    def _rewrite_net_interfaces_file(self, dev, mac, vhost_ip, netmask, gateway_ip):
        with settings(warn_only = True):
            result = local('grep \"iface vhost0\" /etc/network/interfaces')
        if result.succeeded :
            print "Interface vhost0 is already present in /etc/network/interfaces"
            print "Skipping rewrite of this file"
            return
        #endif

        vlan = False
        if os.path.isfile ('/proc/net/vlan/%s' % dev):
            vlan_info = open('/proc/net/vlan/config').readlines()
            match  = re.search('^%s.*\|\s+(\S+)$'%dev, "\n".join(vlan_info), flags=re.M|re.I)
            if not match:
                raise RuntimeError, 'Configured vlan %s is not found in /proc/net/vlan/config'%dev
            phydev = match.group(1)
            vlan = True

        # Replace strings matching dev to vhost0 in ifup and ifdown parts file
        # Any changes to the file/logic with static routes has to be
        # reflected in setup-vnc-static-routes.py too
        ifup_parts_file = os.path.join(os.path.sep, 'etc', 'network', 'if-up.d', 'routes')
        ifdown_parts_file = os.path.join(os.path.sep, 'etc', 'network', 'if-down.d', 'routes')

        if os.path.isfile(ifup_parts_file) and os.path.isfile(ifdown_parts_file):
            with settings(warn_only = True):
                local("sudo sed -i 's/%s/vhost0/g' %s" %(dev, ifup_parts_file))
                local("sudo sed -i 's/%s/vhost0/g' %s" %(dev, ifdown_parts_file))

        temp_intf_file = '%s/interfaces' %(self._temp_dir_name)
        local("cp /etc/network/interfaces %s" %(temp_intf_file))
        with open('/etc/network/interfaces', 'r') as fd:
            cfg_file = fd.read()

        if not self._args.non_mgmt_ip:
            # remove entry from auto <dev> to auto excluding these pattern
            # then delete specifically auto <dev> 
            local("sed -i '/auto %s/,/auto/{/auto/!d}' %s" %(dev, temp_intf_file))
            local("sed -i '/auto %s/d' %s" %(dev, temp_intf_file))
            # add manual entry for dev
            local("echo 'auto %s' >> %s" %(dev, temp_intf_file))
            local("echo 'iface %s inet manual' >> %s" %(dev, temp_intf_file))
            local("echo '    pre-up ifconfig %s up' >> %s" %(dev, temp_intf_file))
            local("echo '    post-down ifconfig %s down' >> %s" %(dev, temp_intf_file))
            if vlan:
                local("echo '    vlan-raw-device %s' >> %s" %(phydev, temp_intf_file))
            if 'bond' in dev.lower():
                iters = re.finditer('^\s*auto\s', cfg_file, re.M)
                indices = [match.start() for match in iters]
                matches = map(cfg_file.__getslice__, indices, indices[1:] + [len(cfg_file)])
                for each in matches:
                    each = each.strip()
                    if re.match('^auto\s+%s'%dev, each):
                        string = ''
                        for lines in each.splitlines():
                            if 'bond-' in lines:
                                string += lines+os.linesep
                        local("echo '%s' >> %s" %(string, temp_intf_file))
                    else:
                        continue
            local("echo '' >> %s" %(temp_intf_file))
        else:
            #remove ip address and gateway
            with settings(warn_only = True):
                local("sed -i '/iface %s inet static/, +2d' %s" % (dev, temp_intf_file))
                local("sed -i '/auto %s/ a\iface %s inet manual\\n    pre-up ifconfig %s up\\n    post-down ifconfig %s down\' %s"% (dev, dev, dev, dev, temp_intf_file))

        # populte vhost0 as static
        local("echo '' >> %s" %(temp_intf_file))
        local("echo 'auto vhost0' >> %s" %(temp_intf_file))
        local("echo 'iface vhost0 inet static' >> %s" %(temp_intf_file))
        local("echo '    pre-up %s/if-vhost0' >> %s" %(contrail_bin_dir, temp_intf_file))
        local("echo '    netmask %s' >> %s" %(netmask, temp_intf_file))
        local("echo '    network_name application' >> %s" %(temp_intf_file))
        if vhost_ip:
            local("echo '    address %s' >> %s" %(vhost_ip, temp_intf_file))
        if (not self._args.non_mgmt_ip) and gateway_ip:
            local("echo '    gateway %s' >> %s" %(gateway_ip, temp_intf_file))

        domain = self.get_domain_search_list()
        if domain:
            local("echo '    dns-search %s' >> %s" %(domain, temp_intf_file))
        dns_list = self.get_dns_servers(dev)
        if dns_list:
            local("echo -n '    dns-nameservers' >> %s" %(temp_intf_file))
            for dns in dns_list:
                local("echo -n ' %s' >> %s" %(dns, temp_intf_file))
        local("echo '\n' >> %s" %(temp_intf_file))

        # move it to right place
        local("sudo mv -f %s /etc/network/interfaces" %(temp_intf_file))

    #end _rewrite_net_interfaces_file

    def fixup_config_files(self):
        pdist = platform.dist()[0]
        temp_dir_name = self._temp_dir_name
        hostname = socket.gethostname()
        cfgm_ip = self._args.cfgm_ip
        collector_ip = self._args.collector_ip
        use_certs = True if self._args.use_certs else False
        contrail_openstack = not(getattr(self._args, 'no_contrail_openstack', False))
        nova_conf_file = "/etc/nova/nova.conf"
        cinder_conf_file = "/etc/cinder/cinder.conf"
        if (os.path.isdir("/etc/openstack_dashboard")):
            dashboard_setting_file = "/etc/openstack_dashboard/local_settings"
        else:
            dashboard_setting_file = "/etc/openstack-dashboard/local_settings"

        if pdist == 'Ubuntu':
            local("ln -sf /bin/true /sbin/chkconfig")

        # TODO till post of openstack-horizon.spec is fixed...
        if 'openstack' in self._args.role:
            if pdist == 'fedora' or pdist == 'centos' or pdist == 'redhat':
                local("sudo sed -i 's/ALLOWED_HOSTS =/#ALLOWED_HOSTS =/g' %s" %(dashboard_setting_file))

            if os.path.exists(nova_conf_file):
                local("sudo sed -i 's/rpc_backend = nova.openstack.common.rpc.impl_qpid/#rpc_backend = nova.openstack.common.rpc.impl_qpid/g' %s" \
                       % (nova_conf_file))
            if os.path.exists(cinder_conf_file):
                local("sudo sed -i 's/rpc_backend = cinder.openstack.common.rpc.impl_qpid/#rpc_backend = cinder.openstack.common.rpc.impl_qpid/g' %s" \
                       % (cinder_conf_file))
            
        """
        glance_ver = local('rpm -q --qf  "%{VERSION}\n" openstack-glance')
        local('sed -ibak "s/max_connections.*/max_connections=10000/" %s' % self.mysql_conf)
        """

        # Put hostname/ip mapping into /etc/hosts to avoid DNS resolution failing at bootup (Cassandra can fail)
        if 'database' in self._args.role:
            database_listen_ip = self._args.database_listen_ip
            hosts_entry = '%s %s' %(database_listen_ip, hostname)
            with settings( warn_only= True) :
                local('grep -q \'%s\' /etc/hosts || echo \'%s\' >> /etc/hosts' %(database_listen_ip, hosts_entry))
        
        if contrail_openstack:
        # Disable selinux
            with lcd(temp_dir_name):
                with settings(warn_only = True):
                    local("sudo sed 's/SELINUX=.*/SELINUX=disabled/g' /etc/selinux/config > config.new")
                    local("sudo mv config.new /etc/selinux/config")
                    local("setenforce 0")
                    # cleanup in case move had error
                    local("rm config.new")

            # Disable iptables
            with settings(warn_only = True):
                local("sudo chkconfig iptables off")
                local("sudo iptables --flush")

            # usable core dump
            initf = '/etc/sysconfig/init'
            with settings(warn_only = True):
                local("sudo sed '/DAEMON_COREFILE_LIMIT=.*/d' %s > %s.new" %(initf, initf))
                local("sudo mv %s.new %s" %(initf, initf))

            if pdist == 'centos' or pdist == 'fedora' or pdist == 'redhat':
                core_unlim = "echo DAEMON_COREFILE_LIMIT=\"'unlimited'\""
                local("%s >> %s" %(core_unlim, initf))
                if pdist == 'Ubuntu':
                    local('mkdir -p /var/crash')
        
            #Core pattern
            pattern= 'kernel.core_pattern = /var/crashes/core.%e.%p.%h.%t'
            ip_fwd_setting = 'net.ipv4.ip_forward = 1'
            sysctl_file = '/etc/sysctl.conf'
            print pattern
            with settings( warn_only= True) :
                local('grep -q \'%s\' /etc/sysctl.conf || echo \'%s\' >> /etc/sysctl.conf' %(pattern, pattern))
                local("sudo sed 's/net.ipv4.ip_forward.*/%s/g' %s > /tmp/sysctl.new" %(ip_fwd_setting,sysctl_file))
                local("sudo mv /tmp/sysctl.new %s" %(sysctl_file))
                local("rm /tmp/sysctl.new")
                local('sysctl -p')
                local('mkdir -p /var/crashes')

            try:
                if pdist == 'fedora' or pdist == 'centos' or pdist == 'redhat':
                    self.enable_kernel_core ()
                if pdist == 'Ubuntu':
                    self.setup_crashkernel_params()
            except Exception as e:
                print "Ignoring failure kernel core dump"
 
        with settings(warn_only = True):
            # analytics venv instalation
            if os.path.exists('/opt/contrail/analytics-venv/archive') and os.path.exists('/opt/contrail/analytics-venv/bin/activate'):
                with lcd("/opt/contrail/analytics-venv/archive"):
                    if os.listdir('/opt/contrail/analytics-venv/archive'):
                        local("bash -c 'source ../bin/activate && pip install *'")
 
            # api venv instalation
            if os.path.exists('/opt/contrail/api-venv/archive') and os.path.exists('/opt/contrail/api-venv/bin/activate'):
                with lcd("/opt/contrail/api-venv/archive"):
                    if os.listdir('/opt/contrail/api-venv/archive'):
                        local("bash -c 'source ../bin/activate && pip install *'")
 
        # vrouter venv instalation
        if os.path.exists('/opt/contrail/vrouter-venv/archive') and os.path.exists('/opt/contrail/vrouter-venv/bin/activate'):
            with lcd("/opt/contrail/vrouter-venv/archive"):
                if os.listdir('/opt/contrail/vrouter-venv/archive'):
                    local("bash -c 'source ../bin/activate && pip install *'")
 
        # control venv instalation
        if os.path.exists('/opt/contrail/control-venv/archive') and os.path.exists('/opt/contrail/control-venv/bin/activate'):
            with lcd("/opt/contrail/control-venv/archive"):
                if os.listdir('/opt/contrail/control-venv/archive'):
                    local("bash -c 'source ../bin/activate && pip install *'")
 
        # database venv instalation
        if os.path.exists('/opt/contrail/database-venv/archive') and os.path.exists('/opt/contrail/database-venv/bin/activate'):
            with lcd("/opt/contrail/database-venv/archive"):
                if os.listdir('/opt/contrail/database-venv/archive'):
                    local("bash -c 'source ../bin/activate && pip install *'")

        if 'openstack' in self._args.role:
            pdist = platform.dist()[0]
            if pdist in ['Ubuntu']:
                mysql_conf = '/etc/mysql/my.cnf'
            elif pdist in ['centos', 'redhat']:
                mysql_conf = '/etc/my.cnf'
            local('sed -i -e "s/bind-address/#bind-address/" %s' % mysql_conf)
            self.service_token = self._args.service_token
            if not self.service_token:
                local("sudo ./contrail_setup_utils/setup-service-token.sh")

            with settings(warn_only = True):
                #comment out parameters from /etc/nova/api-paste.ini
                local("sudo sed -i 's/auth_host = /;auth_host = /' /etc/nova/api-paste.ini")
                local("sudo sed -i 's/auth_port = /;auth_port = /' /etc/nova/api-paste.ini")
                local("sudo sed -i 's/auth_protocol = /;auth_protocol = /' /etc/nova/api-paste.ini")
                local("sudo sed -i 's/admin_tenant_name = /;admin_tenant_name = /' /etc/nova/api-paste.ini")
                local("sudo sed -i 's/admin_user = /;admin_user = /' /etc/nova/api-paste.ini")
                local("sudo sed -i 's/admin_password = /;admin_password = /' /etc/nova/api-paste.ini")

                #comment out parameters from /etc/cinder/api-paste.ini
                local("sudo sed -i 's/auth_host = /;auth_host = /' /etc/cinder/api-paste.ini")
                local("sudo sed -i 's/auth_port = /;auth_port = /' /etc/cinder/api-paste.ini")
                local("sudo sed -i 's/auth_protocol = /;auth_protocol = /' /etc/cinder/api-paste.ini")
                local("sudo sed -i 's/admin_tenant_name = /;admin_tenant_name = /' /etc/cinder/api-paste.ini")
                local("sudo sed -i 's/admin_user = /;admin_user = /' /etc/cinder/api-paste.ini")
                local("sudo sed -i 's/admin_password = /;admin_password = /' /etc/cinder/api-paste.ini")

        if (contrail_openstack and 'compute' in self._args.role):
            with settings(warn_only = True):
                if pdist == 'Ubuntu':
                    cmd = "dpkg -l | grep 'ii' | grep nova-compute | grep -v vif | grep -v nova-compute-kvm | awk '{print $3}'"
                    nova_compute_version = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                    if (nova_compute_version != "2:2013.1.3-0ubuntu1"):
                        local("openstack-config --set /etc/nova/nova.conf DEFAULT neutron_admin_auth_url http://%s:5000/v2.0" % self._args.keystone_ip)

            if os.path.exists(nova_conf_file):
                local("sudo sed -i 's/rpc_backend = nova.openstack.common.rpc.impl_qpid/#rpc_backend = nova.openstack.common.rpc.impl_qpid/g' %s" \
                       % (nova_conf_file))

        if ('config' in self._args.role or
            (contrail_openstack and 'compute' in self._args.role) or
            'openstack' in self._args.role):
            # check if service token passed as argument else
            # get service token from openstack(role) node and fix local config
            self.service_token = self._args.service_token
            self.haproxy = self._args.haproxy
            keystone_ip = self._args.keystone_ip
            ks_auth_protocol = self._args.ks_auth_protocol
            compute_ip = self._args.compute_ip
            cfgm_ip = self._args.cfgm_ip
            quantum_port = self._args.quantum_port
            quantum_service_protocol = self._args.quantum_service_protocol
            if not self.service_token:
                with settings(host_string = 'root@%s' %(keystone_ip), password = env.password):
                    get("/etc/contrail/service.token", temp_dir_name)
                    tok_fd = open('%s/service.token' %(temp_dir_name))
                    self.service_token = tok_fd.read().strip()
                    tok_fd.close()
                    local("cp -f  %s/service.token /etc/contrail/service.token" % temp_dir_name)
                    local("rm %s/service.token" %(temp_dir_name))

            local("echo 'SERVICE_TOKEN=%s' >> %s/ctrl-details" 
                                            %(self.service_token, temp_dir_name))
            local("echo 'AUTH_PROTOCOL=%s' >> %s/ctrl-details" 
                                            %(ks_auth_protocol, temp_dir_name))
            local("echo 'QUANTUM_PROTOCOL=%s' >> %s/ctrl-details" 
                                            %(quantum_service_protocol, temp_dir_name))
            local("echo 'ADMIN_TOKEN=%s' >> %s/ctrl-details" %(ks_admin_password, temp_dir_name))
            local("echo 'CONTROLLER=%s' >> %s/ctrl-details" %(keystone_ip, temp_dir_name))
            if self._args.mgmt_self_ip:
                local("echo 'SELF_MGMT_IP=%s' >> %s/ctrl-details" %(self._args.mgmt_self_ip, temp_dir_name))
            if self._args.openstack_ip_list:
                local("echo 'MEMCACHED_SERVERS=%s' >> %s/ctrl-details" % (':11211,'.join(self._args.openstack_ip_list) + ':11211', temp_dir_name))
            #if 'compute' in self._args.role:
            #    local("echo 'AMQP_SERVER=%s' >> %s/ctrl-details" % (':5672,'.join(self._args.amqp_server_ip_list) + ':5672', temp_dir_name))
            #else:
            #    local("echo 'AMQP_SERVER=%s' >> %s/ctrl-details" % (self._args.amqp_server_ip, temp_dir_name))
            local("echo 'AMQP_SERVER=%s' >> %s/ctrl-details" % (self._args.amqp_server_ip, temp_dir_name))
            if self.haproxy:
                local("echo 'QUANTUM=127.0.0.1' >> %s/ctrl-details" %(temp_dir_name))
            else:
                local("echo 'QUANTUM=%s' >> %s/ctrl-details" %(cfgm_ip, temp_dir_name))
            local("echo 'QUANTUM_PORT=%s' >> %s/ctrl-details" %(quantum_port,
                                                                temp_dir_name))
            local("echo 'COMPUTE=%s' >> %s/ctrl-details" %(compute_ip, temp_dir_name))
            if 'compute' in self._args.role:
                local("echo 'CONTROLLER_MGMT=%s' >> %s/ctrl-details" %(self._args.openstack_mgmt_ip, temp_dir_name))
                if self._args.vmware:
                    local("echo 'VMWARE_IP=%s' >> %s/ctrl-details" %(self._args.vmware, temp_dir_name))
                    local("echo 'VMWARE_USERNAME=%s' >> %s/ctrl-details" %(self._args.vmware_username, temp_dir_name))
                    local("echo 'VMWARE_PASSWD=%s' >> %s/ctrl-details" %(self._args.vmware_passwd, temp_dir_name))
                    local("echo 'VMWARE_VMPG_VSWITCH=%s' >> %s/ctrl-details" %(self._args.vmware_vmpg_vswitch, temp_dir_name))

            if self._args.internal_vip:
                local("echo 'INTERNAL_VIP=%s' >> %s/ctrl-details" % (self._args.internal_vip, temp_dir_name))
            if self._args.contrail_internal_vip:
                local("echo 'CONTRAIL_INTERNAL_VIP=%s' >> %s/ctrl-details" % (self._args.contrail_internal_vip, temp_dir_name))
            elif self._args.internal_vip:
                # Openstack and config in same HA nodes, so sharing same VIP
                local("echo 'CONTRAIL_INTERNAL_VIP=%s' >> %s/ctrl-details" % (self._args.internal_vip, temp_dir_name))
            if self._args.external_vip:
                local("echo 'EXTERNAL_VIP=%s' >> %s/ctrl-details" % (self._args.external_vip, temp_dir_name))
            elif self._args.internal_vip:
                # Single interface setup so both INTERNAL_VIP and EXTERNAL_VIP are same.
                local("echo 'EXTERNAL_VIP=%s' >> %s/ctrl-details" % (self._args.internal_vip, temp_dir_name))
            if self._args.openstack_index:
                local("echo 'OPENSTACK_INDEX=%s' >> %s/ctrl-details" % (self._args.openstack_index, temp_dir_name))
            local("sudo cp %s/ctrl-details /etc/contrail/ctrl-details" %(temp_dir_name))
            local("rm %s/ctrl-details" %(temp_dir_name))
            if os.path.exists("/etc/neutron/neutron.conf"):
                openstack_network_conf_file = "/etc/neutron/neutron.conf"
                network_service = "neutron"
                local("sudo sed -i 's/rpc_backend\s*=\s*%s.openstack.common.rpc.impl_qpid/#rpc_backend = %s.openstack.common.rpc.impl_qpid/g' %s" \
                       % (network_service, network_service, openstack_network_conf_file))
            elif os.path.exists("/etc/quantum/quantum.conf"):
                openstack_network_conf_file = "/etc/quantum/quantum.conf"
                network_service = "quantum"
                local("sudo sed -i 's/rpc_backend\s*=\s*%s.openstack.common.rpc.impl_qpid/#rpc_backend = %s.openstack.common.rpc.impl_qpid/g' %s" \
                       % (network_service, network_service, openstack_network_conf_file))

        if 'database' in self._args.role:
            if pdist == 'fedora' or pdist == 'centos' or pdist == 'redhat':
                CASSANDRA_CONF = '/etc/cassandra/conf'
                CASSANDRA_CONF_FILE = 'cassandra.yaml'
                CASSANDRA_ENV_FILE = 'cassandra-env.sh'
            if pdist == 'Ubuntu':
                CASSANDRA_CONF = '/etc/cassandra/'
                CASSANDRA_CONF_FILE = 'cassandra.yaml'
                CASSANDRA_ENV_FILE = 'cassandra-env.sh'
            listen_ip = self._args.database_listen_ip
            cassandra_dir = self._args.database_dir
            initial_token = self._args.database_initial_token
            seed_list = self._args.database_seed_list
            data_dir = self._args.data_dir
            analytics_data_dir = self._args.analytics_data_dir
            ssd_data_dir = self._args.ssd_data_dir
            if not cassandra_dir:
                raise ArgumentError('Undefined cassandra directory')
            conf_dir = CASSANDRA_CONF
            cnd = os.path.exists(conf_dir)
            conf_file = os.path.join(conf_dir, CASSANDRA_CONF_FILE)
            cnd = cnd and os.path.exists(conf_file)
            if not cnd:
                raise ArgumentError('%s does not appear to be a cassandra source directory' % cassandra_dir)

            self.replace_in_file(conf_file, 'listen_address: ', 'listen_address: ' + listen_ip)
            self.replace_in_file(conf_file, 'cluster_name: ', 'cluster_name: \'Contrail\'')
            self.replace_in_file(conf_file, 'rpc_address: ', 'rpc_address: ' + listen_ip)
            self.replace_in_file(conf_file, '# num_tokens: 256', 'num_tokens: 256')
            self.replace_in_file(conf_file, 'initial_token:', '# initial_token:')
            if data_dir:
                saved_cache_dir = os.path.join(data_dir, 'saved_caches')
                self.replace_in_file(conf_file, 'saved_caches_directory:', 'saved_caches_directory: ' + saved_cache_dir)
                commit_log_dir = os.path.join(data_dir, 'commitlog')
                self.replace_in_file(conf_file, 'commitlog_directory:', 'commitlog_directory: ' + commit_log_dir)
                cass_data_dir = os.path.join(data_dir, 'data')
                self.replace_in_file(conf_file, '    - /var/lib/cassandra/data', '    - ' + cass_data_dir)
            if ssd_data_dir:
                commit_log_dir = os.path.join(ssd_data_dir, 'commitlog')
                self.replace_in_file(conf_file, 'commitlog_directory:', 'commitlog_directory: ' + commit_log_dir)
            if analytics_data_dir:
                if not data_dir:
                    data_dir = '/var/lib/cassandra/data'
                analytics_dir_link = os.path.join(data_dir, 'ContrailAnalytics')
                analytics_dir = os.path.join(analytics_data_dir, 'ContrailAnalytics')
                if not os.path.exists(analytics_dir_link):
                    local("sudo mkdir -p %s" % (analytics_dir))
                    local("sudo ln -s %s %s" % (analytics_dir, analytics_dir_link))
            if seed_list:
                self.replace_in_file(conf_file, '          - seeds: ', '          - seeds: "' + ", ".join(seed_list) + '"')    

            env_file = os.path.join(conf_dir, CASSANDRA_ENV_FILE)
            cnd = os.path.exists(env_file)
            if not cnd:
                raise ArgumentError('%s does not appear to be a cassandra source directory' % cassandra_dir)

            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:+PrintGCDetails\"/JVM_OPTS=\"\$JVM_OPTS -XX:+PrintGCDetails\"/g' %s" \
                  % (env_file))
            distver = platform.dist()[1]
            if  (pdist == 'centos' and distver == '6.5') or pdist == 'redhat':
                local("sudo sed -i 's/JVM_OPTS=\"\$JVM_OPTS -Xss180k\"/JVM_OPTS=\"\$JVM_OPTS -Xss228k\"/g' %s" \
                  % (env_file))
            else:
                local("sudo sed -i 's/JVM_OPTS=\"\$JVM_OPTS -Xss180k\"/JVM_OPTS=\"\$JVM_OPTS -Xss220k\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:+PrintGCDateStamps\"/JVM_OPTS=\"\$JVM_OPTS -XX:+PrintGCDateStamps\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:+PrintHeapAtGC\"/JVM_OPTS=\"\$JVM_OPTS -XX:+PrintHeapAtGC\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:+PrintTenuringDistribution\"/JVM_OPTS=\"\$JVM_OPTS -XX:+PrintTenuringDistribution\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:+PrintGCApplicationStoppedTime\"/JVM_OPTS=\"\$JVM_OPTS -XX:+PrintGCApplicationStoppedTime\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:+PrintPromotionFailure\"/JVM_OPTS=\"\$JVM_OPTS -XX:+PrintPromotionFailure\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -XX:PrintFLSStatistics=1\"/JVM_OPTS=\"\$JVM_OPTS -XX:PrintFLSStatistics=1\"/g' %s" \
                  % (env_file))
            local("sudo sed -i 's/# JVM_OPTS=\"\$JVM_OPTS -Xloggc:\/var\/log\/cassandra\/gc-`date +%%s`.log\"/JVM_OPTS=\"\$JVM_OPTS -Xloggc:\/var\/log\/cassandra\/gc-`date +%%s`.log\"/g' %s" \
                  % (env_file))
	    template_vals = {
                            '__contrail_discovery_ip__': cfgm_ip
                            }
            self._template_substitute_write(database_nodemgr_param_template.template,
                                            template_vals, temp_dir_name + '/database_nodemgr_param')
            self._template_substitute_write(contrail_nodemgr_database_template.template,
                                            template_vals, temp_dir_name + '/contrail-nodemgr-database.conf')
            local("sudo mv %s/database_nodemgr_param /etc/contrail/database_nodemgr_param" %(temp_dir_name))
            local("sudo mv %s/contrail-nodemgr-database.conf /etc/contrail/contrail-nodemgr-database.conf" %(temp_dir_name))

            # set high session timeout to survive glance led disk activity
            local('sudo echo "maxSessionTimeout=120000" >> /etc/zookeeper/conf/zoo.cfg')
            local('sudo echo "autopurge.purgeInterval=3" >> /etc/zookeeper/conf/zoo.cfg')
            local("sudo sed 's/^#log4j.appender.ROLLINGFILE.MaxBackupIndex=/log4j.appender.ROLLINGFILE.MaxBackupIndex=/g' /etc/zookeeper/conf/log4j.properties > log4j.properties.new")
            local("sudo mv log4j.properties.new /etc/zookeeper/conf/log4j.properties")
            if pdist == 'fedora' or pdist == 'centos' or pdist == 'redhat':
                local('echo export ZOO_LOG4J_PROP="INFO,CONSOLE,ROLLINGFILE" >> /usr/lib/zookeeper/bin/zkEnv.sh')
            if pdist == 'Ubuntu':
                local('echo ZOO_LOG4J_PROP="INFO,CONSOLE,ROLLINGFILE" >> /etc/zookeeper/conf/environment')

            zk_index = 1
            for zk_ip in self._args.zookeeper_ip_list:
                local('sudo echo "server.%d=%s:2888:3888" >> /etc/zookeeper/conf/zoo.cfg' %(zk_index, zk_ip))
                zk_index = zk_index + 1

            #put cluster-unique zookeeper's instance id in myid
            local('sudo echo "%s" > /var/lib/zookeeper/myid' %(self._args.database_index))

        if 'collector' in self._args.role:
            self_collector_ip = self._args.self_collector_ip
            cassandra_server_list = [(cassandra_server_ip, '9160') for cassandra_server_ip in self._args.cassandra_ip_list]
            template_vals = {'__contrail_log_file__' : '/var/log/contrail/collector.log',
                             '__contrail_log_local__': '--log-local',
                             '__contrail_discovery_ip__' : cfgm_ip,
                             '__contrail_host_ip__' : self_collector_ip,
                             '__contrail_listen_port__' : '8086',
                             '__contrail_http_server_port__' : '8089',
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list),
                             '__contrail_analytics_data_ttl__' : self._args.analytics_data_ttl,
                             '__contrail_analytics_syslog_port__' : str(self._args.analytics_syslog_port)}
            self._template_substitute_write(vizd_param_template.template,
                                           template_vals, temp_dir_name + '/contrail-collector.conf')
            local("sudo mv %s/contrail-collector.conf /etc/contrail/contrail-collector.conf" %(temp_dir_name))

            template_vals = {'__contrail_log_file__' : '/var/log/contrail/query-engine.log',
                             '__contrail_redis_server__': '127.0.0.1',
                             '__contrail_redis_server_port__' : '6379',
                             '__contrail_http_server_port__' : '8091',
                             '__contrail_collector__' : '127.0.0.1',
                             '__contrail_collector_port__' : '8086',
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list)}
            self._template_substitute_write(qe_param_template.template,
                                            template_vals, temp_dir_name + '/contrail-query-engine.conf')
            local("sudo mv %s/contrail-query-engine.conf /etc/contrail/contrail-query-engine.conf" %(temp_dir_name))
           
            rest_api_port = '8081'
            if self._args.internal_vip:
                rest_api_port = '9081'
            template_vals = {'__contrail_log_file__' : '/var/log/contrail/contrail-analytics-api.log',
                             '__contrail_log_local__': '0',
                             '__contrail_log_category__': '',
                             '__contrail_log_level__': 'SYS_DEBUG',
                             '__contrail_redis_server_port__' : '6379',
                             '__contrail_redis_query_port__' : '6379',
                             '__contrail_http_server_port__' : '8090',
                             '__contrail_rest_api_port__' : rest_api_port,
                             '__contrail_host_ip__' : self_collector_ip, 
                             '__contrail_discovery_ip__' : cfgm_ip,
                             '__contrail_discovery_port__' : 5998,
                             '__contrail_collector__': self_collector_ip,
                             '__contrail_collector_port__': '8086',
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list)}
            self._template_substitute_write(opserver_param_template.template,
                                            template_vals, temp_dir_name + '/opserver_param')
            local("sudo mv %s/opserver_param /etc/contrail/contrail-analytics-api.conf" %(temp_dir_name))
                    
        if 'config' in self._args.role:
            keystone_ip = self._args.keystone_ip
            region_name = self._args.region_name
            ks_auth_protocol = self._args.ks_auth_protocol
            ks_auth_port = self._args.ks_auth_port
            ks_admin_token = self._args.ks_admin_token
            ks_insecure = self._args.ks_insecure
            cassandra_server_list = [(cassandra_server_ip, '9160') for cassandra_server_ip in self._args.cassandra_ip_list]
            zk_servers = ','.join(self._args.zookeeper_ip_list)
            zk_servers_ports = ','.join(['%s:2181' %(s) for s in self._args.zookeeper_ip_list])
            rabbit_host = cfgm_ip
            rabbit_port = 5672
            if self._args.internal_vip:
                rabbit_host = self._args.internal_vip
                rabbit_port = 5672

            if pdist == 'Ubuntu':
                # log4j.properties
                template_vals = {
                                }
                self._template_substitute_write(ifmap_log4j_template.template,
                                                template_vals, temp_dir_name + '/log4j.properties')
                local("sudo mv %s/log4j.properties /etc/ifmap-server/" %(temp_dir_name))
                # authorization.properties
                template_vals = {
                                }
                self._template_substitute_write(ifmap_authorization_template.template,
                                                template_vals, temp_dir_name + '/authorization.properties')
                local("sudo mv %s/authorization.properties /etc/ifmap-server/" %(temp_dir_name))
                # basicauthusers.properties
                template_vals = {
                                }
                self._template_substitute_write(ifmap_basicauthusers_template.template,
                                                template_vals, temp_dir_name + '/basicauthusers.properties')
                local("sudo mv %s/basicauthusers.properties /etc/ifmap-server/" %(temp_dir_name))
                # publisher.properties
                template_vals = {
                                }
                self._template_substitute_write(ifmap_publisher_template.template,
                                                template_vals, temp_dir_name + '/publisher.properties')
                local("sudo mv %s/publisher.properties /etc/ifmap-server/" %(temp_dir_name))

            # contrail-api.conf
            template_vals = {'__contrail_ifmap_server_ip__': cfgm_ip,
                             '__contrail_ifmap_server_port__': '8444' if use_certs else '8443',
                             '__contrail_ifmap_username__': 'api-server',
                             '__contrail_ifmap_password__': 'api-server',
                             '__contrail_listen_ip_addr__': '0.0.0.0',
                             '__contrail_listen_port__': '8082',
                             '__contrail_use_certs__': use_certs,
                             '__contrail_keyfile_location__': '/etc/contrail/ssl/private_keys/apiserver_key.pem',
                             '__contrail_certfile_location__': '/etc/contrail/ssl/certs/apiserver.pem',
                             '__contrail_cacertfile_location__': '/etc/contrail/ssl/certs/ca.pem',
                             '__contrail_multi_tenancy__': self._args.multi_tenancy,
                             '__contrail_keystone_ip__': keystone_ip,
                             '__rabbit_server_ip__': self._args.internal_vip or rabbit_host,
                             '__rabbit_server_port__': rabbit_port,
                             '__contrail_admin_user__': ks_admin_user,
                             '__contrail_admin_password__': ks_admin_password,
                             '__contrail_admin_tenant_name__': ks_admin_tenant_name,
                             '__contrail_admin_token__': ks_admin_token,
                             '__contrail_ks_auth_protocol__': ks_auth_protocol,
                             '__contrail_ks_auth_port__': ks_auth_port,
                             '__keystone_insecure_flag__': ks_insecure,
                             '__contrail_memcached_opt__': 'memcache_servers=127.0.0.1:11211' if self._args.multi_tenancy else '',
                             '__contrail_log_file__': '/var/log/contrail/api.log',
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list),
                             '__contrail_disc_server_ip__': self._args.internal_vip or cfgm_ip,
                             '__contrail_disc_server_port__': '5998',
                             '__contrail_zookeeper_server_ip__': zk_servers_ports,
                            }
            self._template_substitute_write(api_server_conf_template.template,
                                            template_vals, temp_dir_name + '/contrail-api.conf')
            local("sudo mv %s/contrail-api.conf /etc/contrail/" %(temp_dir_name))

            # supervisor contrail-api.ini
            n_api_workers = self._args.n_api_workers
            template_vals = {'__contrail_api_port_base__': '910', # 910x
                             '__contrail_api_nworkers__': n_api_workers,
                            }
            if pdist == 'Ubuntu':
                tmpl = contrail_api_ini_template.template
            else:
                tmpl = contrail_api_ini_centos_template.template

            self._template_substitute_write(tmpl,
                                            template_vals, temp_dir_name + '/contrail-api.ini')
            local("sudo mv %s/contrail-api.ini /etc/contrail/supervisord_config_files/" %(temp_dir_name))

            # initd script wrapper for contrail-api
            sctl_lines = ''
            for worker_id in range(int(n_api_workers)):
                sctl_line = 'supervisorctl -s http://localhost:9004 ' + \
                            '${1} `basename ${0}:%s`' %(worker_id)
                sctl_lines = sctl_lines + sctl_line

            template_vals = {'__contrail_supervisorctl_lines__': sctl_lines,
                            }
            self._template_substitute_write(contrail_api_svc_template.template,
                                            template_vals, temp_dir_name + '/contrail-api')
            local("sudo mv %s/contrail-api /etc/init.d/" %(temp_dir_name))
            local("sudo chmod a+x /etc/init.d/contrail-api")

            # quantum plugin
            template_vals = {'__contrail_api_server_ip__': self._args.internal_vip or cfgm_ip,
                             '__contrail_api_server_port__': '8082',
                             '__contrail_multi_tenancy__': self._args.multi_tenancy,
                             '__contrail_keystone_ip__': '127.0.0.1',
                             '__contrail_admin_token__': ks_admin_token,
                             '__contrail_ks_auth_protocol__': ks_auth_protocol,
                             '__contrail_ks_auth_port__': ks_auth_port,
                             '__contrail_admin_user__': ks_admin_user,
                             '__contrail_admin_password__': ks_admin_password,
                             '__contrail_admin_tenant_name__': ks_admin_tenant_name,
                        }
            self._template_substitute_write(quantum_conf_template.template,
                                            template_vals, temp_dir_name + '/contrail_plugin.ini')
            if os.path.exists("/etc/neutron"):
                local("sudo mkdir -p /etc/neutron/plugins/opencontrail")
                local("sudo mv %s/contrail_plugin.ini /etc/neutron/plugins/opencontrail/ContrailPlugin.ini" %(temp_dir_name))
            else:
                local("sudo mv %s/contrail_plugin.ini /etc/quantum/plugins/contrail/contrail_plugin.ini" %(temp_dir_name))

            if pdist == 'Ubuntu':
                neutron_def_file = "/etc/default/neutron-server"
                if os.path.exists(neutron_def_file):
                    local("sudo sed -i 's/NEUTRON_PLUGIN_CONFIG=.*/NEUTRON_PLUGIN_CONFIG=\"\/etc\/neutron\/plugins\/opencontrail\/ContrailPlugin.ini\"/g' %s" %(neutron_def_file))

            # schema_transformer.conf
            template_vals = {'__contrail_ifmap_server_ip__': cfgm_ip,
                             '__contrail_ifmap_server_port__': '8444' if use_certs else '8443',
                             '__contrail_ifmap_username__': 'schema-transformer',
                             '__contrail_ifmap_password__': 'schema-transformer',
                             '__contrail_api_server_ip__': self._args.internal_vip or cfgm_ip,
                             '__contrail_api_server_port__': '8082',
                             '__contrail_zookeeper_server_ip__': zk_servers_ports,
                             '__contrail_use_certs__': use_certs,
                             '__contrail_keyfile_location__': '/etc/contrail/ssl/private_keys/schema_xfer_key.pem',
                             '__contrail_certfile_location__': '/etc/contrail/ssl/certs/schema_xfer.pem',
                             '__contrail_cacertfile_location__': '/etc/contrail/ssl/certs/ca.pem',
                             '__contrail_admin_user__': ks_admin_user,
                             '__contrail_admin_password__': ks_admin_password,
                             '__contrail_admin_tenant_name__': ks_admin_tenant_name,
                             '__contrail_admin_token__': ks_admin_token,
                             '__contrail_log_file__' : '/var/log/contrail/schema.log',
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list),
                             '__contrail_disc_server_ip__': self._args.internal_vip or cfgm_ip,
                             '__contrail_disc_server_port__': '5998',
                            }
            self._template_substitute_write(schema_transformer_conf_template.template,
                                            template_vals, temp_dir_name + '/schema_transformer.conf')
            local("sudo mv %s/schema_transformer.conf /etc/contrail/schema_transformer.conf" %(temp_dir_name))

            # svc_monitor.conf
            template_vals = {'__contrail_ifmap_server_ip__': cfgm_ip,
                             '__contrail_ifmap_server_port__': '8444' if use_certs else '8443',
                             '__contrail_ifmap_username__': 'svc-monitor',
                             '__contrail_ifmap_password__': 'svc-monitor',
                             '__contrail_api_server_ip__': self._args.internal_vip or cfgm_ip,
                             '__contrail_api_server_port__': '8082',
                             '__contrail_keystone_ip__': keystone_ip,
                             '__contrail_zookeeper_server_ip__': zk_servers_ports,
                             '__contrail_use_certs__': use_certs,
                             '__contrail_keyfile_location__': '/etc/contrail/ssl/private_keys/svc_monitor_key.pem',
                             '__contrail_certfile_location__': '/etc/contrail/ssl/certs/svc_monitor.pem',
                             '__contrail_cacertfile_location__': '/etc/contrail/ssl/certs/ca.pem',
                             '__contrail_admin_user__': ks_admin_user,
                             '__contrail_admin_password__': ks_admin_password,
                             '__contrail_admin_tenant_name__': ks_admin_tenant_name,
                             '__contrail_admin_token__': ks_admin_token,
                             '__contrail_log_file__' : '/var/log/contrail/svc-monitor.log',
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list),
                             '__contrail_disc_server_ip__': self._args.internal_vip or cfgm_ip,
                             '__contrail_disc_server_port__': '5998',
                             '__contrail_region_name__': region_name,
                            }
            self._template_substitute_write(svc_monitor_conf_template.template,
                                            template_vals, temp_dir_name + '/svc_monitor.conf')
            local("sudo mv %s/svc_monitor.conf /etc/contrail/svc_monitor.conf" %(temp_dir_name))

            # discovery.conf
            template_vals = {
                             '__contrail_zk_server_ip__': zk_servers,
                             '__contrail_zk_server_port__': '2181',
                             '__contrail_listen_ip_addr__': '0.0.0.0',
                             '__contrail_listen_port__': '5998',
                             '__contrail_log_local__': 'True',
                             '__contrail_log_file__': '/var/log/contrail/discovery.log',
                             '__contrail_healthcheck_interval__': 5,
                             '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in cassandra_server_list),
                            }
            self._template_substitute_write(discovery_conf_template.template,
                                            template_vals, temp_dir_name + '/contrail-discovery.conf')
            local("sudo mv %s/contrail-discovery.conf /etc/contrail/" %(temp_dir_name))

            # supervisor contrail-discovery.ini
            template_vals = {'__contrail_disc_port_base__': '911', # 911x
                             '__contrail_disc_nworkers__': '1'
                            }
            if pdist == 'Ubuntu':
                tmpl = contrail_discovery_ini_template.template
            else:
                tmpl = contrail_discovery_ini_centos_template.template

            self._template_substitute_write(tmpl,
                                            template_vals, temp_dir_name + '/contrail-discovery.ini')
            local("sudo mv %s/contrail-discovery.ini /etc/contrail/supervisord_config_files/" %(temp_dir_name))

            # initd script wrapper for contrail-discovery
            sctl_lines = ''
            for worker_id in range(int(n_api_workers)):
                sctl_line = 'supervisorctl -s http://localhost:9004 ' + \
                            '${1} `basename ${0}:%s`' %(worker_id)
                sctl_lines = sctl_lines + sctl_line

            template_vals = {'__contrail_supervisorctl_lines__': sctl_lines,
                            }
            self._template_substitute_write(contrail_discovery_svc_template.template,
                                            template_vals, temp_dir_name + '/contrail-discovery')
            local("sudo mv %s/contrail-discovery /etc/init.d/" %(temp_dir_name))
            local("sudo chmod a+x /etc/init.d/contrail-discovery")

            # vnc_api_lib.ini
            template_vals = {
                             '__contrail_keystone_ip__': keystone_ip,
 			     '__contrail_ks_auth_protocol__': ks_auth_protocol,
 			     '__keystone_insecure_flag__': ks_insecure,
                            }
            self._template_substitute_write(vnc_api_lib_ini_template.template,
                                            template_vals, temp_dir_name + '/vnc_api_lib.ini')
            local("sudo mv %s/vnc_api_lib.ini /etc/contrail/" %(temp_dir_name))

            # Configure rabbitmq config file
            with settings(warn_only = True):
                rabbit_conf = '/etc/rabbitmq/rabbitmq.config'
                if not local('grep \"tcp_listeners.*%s.*5672\" %s' % (cfgm_ip, rabbit_conf)).succeeded:
                    local('sudo echo "[" >> %s' % rabbit_conf)
                    local('sudo echo "   {rabbit, [ {tcp_listeners, [{\\"%s\\", 5672}]}," >> %s' % (cfgm_ip, rabbit_conf))
                    local('sudo echo "   {loopback_users, []}," >> %s' % rabbit_conf)
                    local('sudo echo "   {log_levels,[{connection, info},{mirroring, info}]} ]" >> %s' % rabbit_conf)
                    local('sudo echo "    }" >> %s' % rabbit_conf)
                    local('sudo echo "]." >> %s' % rabbit_conf)

        if 'control' in self._args.role:
            control_ip = self._args.control_ip
            certdir = '/var/lib/puppet/ssl' if self._args.puppet_server else '/etc/contrail/ssl'
            template_vals = {'__contrail_ifmap_usr__': '%s' %(control_ip),
                             '__contrail_ifmap_paswd__': '%s' %(control_ip),
                             '__contrail_discovery_ip__': cfgm_ip,
                             '__contrail_hostname__': hostname,
                             '__contrail_host_ip__': control_ip,
                             '__contrail_cert_ops__': '%s' %(certdir) if use_certs else '',
                            }
            self._template_substitute_write(bgp_param_template.template,
                                            template_vals, temp_dir_name + '/contrail-control.conf')
            local("sudo mv %s/contrail-control.conf /etc/contrail/contrail-control.conf" %(temp_dir_name))

            dns_template_vals = {'__contrail_ifmap_usr__': '%s.dns' %(control_ip),
                             '__contrail_ifmap_paswd__': '%s.dns' %(control_ip),
                             '__contrail_discovery_ip__': cfgm_ip,
                             '__contrail_hostname__': hostname,
                             '__contrail_host_ip__': control_ip,
                             '__contrail_cert_ops__': '%s' %(certdir) if use_certs else '',
                            }
            self._template_substitute_write(dns_param_template.template,
                                            dns_template_vals, temp_dir_name + '/dns.conf')
            local("sudo mv %s/dns.conf /etc/contrail/dns.conf" %(temp_dir_name))
            if pdist == 'Ubuntu':
                for confl in 'rndc named'.split():
                    local("".join(["sudo perl -pi -e ",
                        "'s/(\\s*secret\\s+\").*\"\\s*;/",
                        "\\1xvysmOR8lnUQRBcunkC6vg==\";/g;'",
                        " /etc/contrail/dns/%s.conf" % confl]))

            with settings(host_string = 'root@%s' %(cfgm_ip), password = env.password):
                if self._args.puppet_server:
                    local("echo '    server = %s' >> /etc/puppet/puppet.conf" \
                        %(self._args.puppet_server))


        if (contrail_openstack and 'compute' in self._args.role):
            dist = platform.dist()[0]
            # add /dev/net/tun in cgroup_device_acl needed for type=ethernet interfaces
            with settings(warn_only = True):
                ret = local("sudo grep -q '^cgroup_device_acl' /etc/libvirt/qemu.conf")
                if ret.return_code == 1:
                    if  dist in ['centos', 'redhat']:
                        local('sudo echo "clear_emulator_capabilities = 1" >> /etc/libvirt/qemu.conf')
                        local('sudo echo \'user = "root"\' >> /etc/libvirt/qemu.conf')
                        local('sudo echo \'group = "root"\' >> /etc/libvirt/qemu.conf')
                    local('sudo echo \'cgroup_device_acl = [\' >> /etc/libvirt/qemu.conf')
                    local('sudo echo \'    "/dev/null", "/dev/full", "/dev/zero",\' >> /etc/libvirt/qemu.conf')
                    local('sudo echo \'    "/dev/random", "/dev/urandom",\' >> /etc/libvirt/qemu.conf')
                    local('sudo echo \'    "/dev/ptmx", "/dev/kvm", "/dev/kqemu",\' >> /etc/libvirt/qemu.conf')
                    local('sudo echo \'    "/dev/rtc", "/dev/hpet","/dev/net/tun",\' >> /etc/libvirt/qemu.conf')
                    local('sudo echo \']\' >> /etc/libvirt/qemu.conf')
                    self._fixed_qemu_conf = True
                # add "alias bridge off" in /etc/modprobe.conf for Centos
                if  dist == 'centos' or dist == 'redhat':
                    local('sudo echo "alias bridge off" > /etc/modprobe.conf')

        if 'compute' in self._args.role :
            self.haproxy = self._args.haproxy
	    ks_auth_protocol = self._args.ks_auth_protocol
            ks_insecure = self._args.ks_insecure

            if self.haproxy:
                template_vals = {'__contrail_discovery_ip__': '127.0.0.1'
                                }
            else:
                template_vals = {'__contrail_discovery_ip__': cfgm_ip
                                }
            # Customized for Workday since, Workday needs only vrouter install and setup
 	    # vnc_api_lib.ini
            template_vals = {
                             '__contrail_keystone_ip__': keystone_ip,
                             '__contrail_ks_auth_protocol__': ks_auth_protocol,
                             '__keystone_insecure_flag__': ks_insecure,
                            }
            self._template_substitute_write(vnc_api_lib_ini_template.template,
                                            template_vals, temp_dir_name + '/vnc_api_lib.ini')
            local("sudo mv %s/vnc_api_lib.ini /etc/contrail/" %(temp_dir_name))

            self._template_substitute_write(agent_param_template.template,
                                            template_vals, temp_dir_name + '/vrouter_nodemgr_param')
            local("sudo mv %s/vrouter_nodemgr_param /etc/contrail/vrouter_nodemgr_param" %(temp_dir_name))

            keystone_ip = self._args.keystone_ip
            compute_ip = self._args.compute_ip
            if self.haproxy:
                discovery_ip = '127.0.0.1'
            else:
                discovery_ip = self._args.cfgm_ip
            ncontrols = self._args.ncontrols
            physical_interface = self._args.physical_interface
            non_mgmt_ip = self._args.non_mgmt_ip 
            non_mgmt_gw = self._args.non_mgmt_gw
            vhost_ip = compute_ip
            vgw_public_subnet = self._args.vgw_public_subnet
            vgw_public_vn_name = self._args.vgw_public_vn_name
            vgw_intf_list = self._args.vgw_intf_list
            vgw_gateway_routes = self._args.vgw_gateway_routes
            multi_net= False
            if non_mgmt_ip :
                multi_net= True
                vhost_ip= non_mgmt_ip

            dev = None
            compute_dev = None
            if physical_interface:
                if physical_interface in netifaces.interfaces ():
                    dev = physical_interface
                else:
                     raise KeyError, 'Interface %s in present' % (
                             physical_interface)
            else:
                # deduce the phy interface from ip, if configured
                dev = self.get_device_by_ip (vhost_ip)
                if multi_net:
                    compute_dev = self.get_device_by_ip (compute_ip)

            mac = None
            if dev and dev != 'vhost0' :
                mac = netifaces.ifaddresses (dev)[netifaces.AF_LINK][0][
                            'addr']
                if mac:
                    with open ('%s/default_pmac' % temp_dir_name, 'w') as f:
                        f.write (mac)
                    with settings(warn_only = True):
                        local("sudo mv %s/default_pmac /etc/contrail/default_pmac" % (temp_dir_name))
                else:
                    raise KeyError, 'Interface %s Mac %s' % (str (dev), str (mac))
                netmask = netifaces.ifaddresses (dev)[netifaces.AF_INET][0][
                                'netmask']
                if multi_net:
                    gateway= non_mgmt_gw
                else:
                    gateway = self.find_gateway (dev)
                cidr = str (netaddr.IPNetwork('%s/%s' % (vhost_ip, netmask)))

                if vgw_public_subnet:
                    with lcd(temp_dir_name):
                        # Manipulating the string to use in agent_param
                        vgw_public_subnet_str=[]
                        for i in vgw_public_subnet[1:-1].split(";"):
                            j=i[1:-1].split(",")
                            j=";".join(j)
                            vgw_public_subnet_str.append(j)
                        vgw_public_subnet_str=str(tuple(vgw_public_subnet_str)).replace("'","")
                        vgw_public_subnet_str=vgw_public_subnet_str.replace(" ","")
                        vgw_intf_list_str=str(tuple(vgw_intf_list[1:-1].split(";"))).replace(" ","")
                
                        local("sudo sed 's@COLLECTOR=.*@COLLECTOR=%s@g;s@dev=.*@dev=%s@g;s@vgw_subnet_ip=.*@vgw_subnet_ip=%s@g;s@vgw_intf=.*@vgw_intf=%s@g' /etc/contrail/agent_param.tmpl > agent_param.new" %(collector_ip, dev,vgw_public_subnet_str,vgw_intf_list_str))
                        local("sudo mv agent_param.new /etc/contrail/agent_param")
                        local("openstack-config --set /etc/nova/nova.conf DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver")
                else:
                    with lcd(temp_dir_name):
                        local("sudo sed 's/COLLECTOR=.*/COLLECTOR=%s/g;s/dev=.*/dev=%s/g' /etc/contrail/agent_param.tmpl > agent_param.new" %(collector_ip, dev))
                        local("sudo mv agent_param.new /etc/contrail/agent_param")
                vmware_dev = ""
                hypervisor_type = "kvm"
                if self._args.vmware:
                    vmware_dev = self.get_secondary_device(dev)
                    hypervisor_type = "vmware"
                vnswad_conf_template_vals = {'__contrail_vhost_ip__': cidr,
                    '__contrail_vhost_gateway__': gateway,
                    '__contrail_discovery_ip__': discovery_ip,
                    '__contrail_discovery_ncontrol__': ncontrols,
                    '__contrail_physical_intf__': dev,
                    '__contrail_control_ip__': compute_ip,
                    '__hypervisor_type__': hypervisor_type,
                    '__vmware_physical_interface__': vmware_dev,
                }
                self._template_substitute_write(vnswad_conf_template.template,
                        vnswad_conf_template_vals, temp_dir_name + '/vnswad.conf')

                if vgw_public_vn_name and vgw_public_subnet:
                    vgw_public_vn_name = vgw_public_vn_name[1:-1].split(';')
                    vgw_public_subnet = vgw_public_subnet[1:-1].split(';')
                    vgw_intf_list = vgw_intf_list[1:-1].split(';')
                    gateway_str = ""
                    if vgw_gateway_routes != None:
                        vgw_gateway_routes = vgw_gateway_routes[1:-1].split(';')
                    for i in range(len(vgw_public_vn_name)):
                        gateway_str += '\n[%s%d]\n' %("GATEWAY-", i)
                        gateway_str += "# Name of the routing_instance for which the gateway is being configured\n"
                        gateway_str += "routing_instance=" + vgw_public_vn_name[i] + "\n\n"
                        gateway_str += "# Gateway interface name\n"
                        gateway_str += "interface=" + vgw_intf_list[i] + "\n\n"
                        gateway_str += "# Virtual network ip blocks for which gateway service is required. Each IP\n"
                        gateway_str += "# block is represented as ip/prefix. Multiple IP blocks are represented by\n"
                        gateway_str += "# separating each with a space\n"
                        gateway_str += "ip_blocks="

                        if vgw_public_subnet[i].find("[") !=-1:
                            for ele in vgw_public_subnet[i][1:-1].split(","):
                                gateway_str += ele[1:-1] + " "
                        else:
                            gateway_str += vgw_public_subnet[i]
                        gateway_str += "\n\n"
                        if vgw_gateway_routes != None and i < len(vgw_gateway_routes):
                            if  vgw_gateway_routes[i] != '[]':
                            	gateway_str += "# Routes to be exported in routing_instance. Each route is represented as\n"
                            	gateway_str += "# ip/prefix. Multiple routes are represented by separating each with a space\n"
                            	gateway_str += "routes="
                                if vgw_gateway_routes[i].find("[") !=-1:
                                    for ele in vgw_gateway_routes[i][1:-1].split(","):
                                        gateway_str += ele[1:-1] + " "
                                else:
                                    gateway_str += vgw_gateway_routes[i]
                                gateway_str += "\n"
                    filename = temp_dir_name + "/vnswad.conf"
                    with open(filename, "a") as f:
                        f.write(gateway_str)

                local("sudo cp %s/vnswad.conf /etc/contrail/contrail-vrouter-agent.conf" %(temp_dir_name))
                local("sudo rm %s/vnswad.conf*" %(temp_dir_name))

                if pdist == 'centos' or pdist == 'fedora' or pdist == 'redhat':
                    ## make ifcfg-vhost0
                    with open ('%s/ifcfg-vhost0' % temp_dir_name, 'w') as f:
                        f.write ('''#Contrail vhost0
DEVICE=vhost0
ONBOOT=yes
BOOTPROTO=none
IPV6INIT=no
USERCTL=yes
IPADDR=%s
NETMASK=%s
NM_CONTROLLED=no
#NETWORK MANAGER BUG WORKAROUND
SUBCHANNELS=1,2,3
''' % (vhost_ip, netmask ))
                        # Don't set gateway and DNS on vhost0 if on non-mgmt network
                        if not multi_net:
                            if gateway:
                                f.write('GATEWAY=%s\n' %( gateway ) )
                            dns_list = self.get_dns_servers(dev)
                            for i, dns in enumerate(dns_list):
                                f.write('DNS%d=%s\n' % (i+1, dns))
                            domain_list = self.get_domain_search_list()
                            if domain_list:
                                f.write('DOMAIN="%s"\n'% domain_list)

                        prsv_cfg = []
                        mtu = self.get_if_mtu (dev)
                        if mtu:
                            dcfg = 'MTU=%s' % str(mtu)
                            f.write(dcfg+'\n')
                            prsv_cfg.append (dcfg)
                        f.flush ()
#            if dev != 'vhost0':
                        with settings(warn_only = True):
                            local("sudo mv %s/ifcfg-vhost0 /etc/sysconfig/network-scripts/ifcfg-vhost0" % (temp_dir_name))
                        ## make ifcfg-$dev
                        if not os.path.isfile (
                                '/etc/sysconfig/network-scripts/ifcfg-%s.rpmsave' % dev):
                            with settings(warn_only = True):
                                local("sudo cp /etc/sysconfig/network-scripts/ifcfg-%s /etc/sysconfig/network-scripts/ifcfg-%s.rpmsave" % (dev, dev))
                        self._rewrite_ifcfg_file('%s/ifcfg-%s' % (temp_dir_name, dev), dev, prsv_cfg)

                        if multi_net :
                            self.migrate_routes(dev)

                        with settings(warn_only = True):
                            local("sudo mv %s/ifcfg-%s /etc/contrail/" % (temp_dir_name, dev))

                            local("sudo chkconfig network on")
                            local("sudo chkconfig supervisor-vrouter on")
			    
                # end pdist == centos | fedora

                if pdist == 'Ubuntu':
                    self._rewrite_net_interfaces_file(dev, mac, vhost_ip, netmask, gateway)
                # end pdist == ubuntu

            else: # of if dev and dev != 'vhost0'
                if not os.path.isfile("/etc/contrail/contrail-vrouter-agent.conf"):
                    if os.path.isfile("/opt/contrail/contrail_installer/contrail_config_templates/agent_xml2ini.py"):
                        local("sudo python /opt/contrail/contrail_installer/contrail_config_templates/agent_xml2ini.py")
            #end if dev and dev != 'vhost0' :

        # role == compute && !cfgm

        if 'webui' in self._args.role:
            openstack_ip = self._args.openstack_ip
            keystone_ip = self._args.keystone_ip
            internal_vip = self._args.internal_vip
            contrail_internal_vip = self._args.contrail_internal_vip or internal_vip
            local("sudo sed \"s/config.cnfg.server_ip.*/config.cnfg.server_ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(contrail_internal_vip or cfgm_ip))
            local("sudo mv config.global.js.new /etc/contrail/config.global.js")
            local("sudo sed \"s/config.networkManager.ip.*/config.networkManager.ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(contrail_internal_vip or cfgm_ip))
            local("sudo mv config.global.js.new /etc/contrail/config.global.js")
            local("sudo sed \"s/config.imageManager.ip.*/config.imageManager.ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(internal_vip or openstack_ip))
            local("sudo mv config.global.js.new /etc/contrail/config.global.js")
            local("sudo sed \"s/config.computeManager.ip.*/config.computeManager.ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(internal_vip or openstack_ip))
            local("sudo mv config.global.js.new /etc/contrail/config.global.js")
            local("sudo sed \"s/config.identityManager.ip.*/config.identityManager.ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(internal_vip or keystone_ip))
            local("sudo mv config.global.js.new /etc/contrail/config.global.js")
            local("sudo sed \"s/config.storageManager.ip.*/config.storageManager.ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(internal_vip or openstack_ip))
            local("sudo mv config.global.js.new /etc/contrail/config.global.js")            
            if collector_ip:
                local("sudo sed \"s/config.analytics.server_ip.*/config.analytics.server_ip = '%s';/g\" /etc/contrail/config.global.js > config.global.js.new" %(contrail_internal_vip or collector_ip))
                local("sudo mv config.global.js.new /etc/contrail/config.global.js")
            if self._args.cassandra_ip_list:
                local("sudo sed \"s/config.cassandra.server_ips.*/config.cassandra.server_ips = %s;/g\" /etc/contrail/config.global.js > config.global.js.new" %(str(self._args.cassandra_ip_list)))
                local("sudo mv config.global.js.new /etc/contrail/config.global.js")    

        if 'config' in self._args.role and self._args.use_certs:
            local("sudo ./contrail_setup_utils/setup-pki.sh /etc/contrail/ssl")

    #end fixup_config_files

    # Customized for Workday
    # Please note that provision_vrouter.py to be executed locally and connect to contrail API
    def add_vnc_config(self):
        if 'compute' in self._args.role:
            cfgm_ip = self._args.cfgm_ip
            compute_ip = self._args.compute_ip
            compute_hostname = socket.gethostname()
            #with settings(host_string = 'root@%s' %(cfgm_ip), password = env.password):
            #with settings(host_string = 'root@%s' %(cfgm_ip)):
            prov_args = "--host_name %s --host_ip %s --api_server_ip %s --oper add " \
                        "--admin_user %s --admin_password %s --admin_tenant_name %s" \
                        %(compute_hostname, compute_ip, cfgm_ip, ks_admin_user, ks_admin_password, ks_admin_tenant_name)
            local("python /opt/contrail/utils/provision_vrouter.py %s" %(prov_args))
    #end add_vnc_config

    def enable_services(self):
        pass
    #end enable_services

    def cleanup(self):
        os.rmdir(self._temp_dir_name)
    #end cleanup

    def do_setup(self):
        #self.setup_repo()
        #self.install_packages()
        # local configuration
        self.fixup_config_files()

        # global vnc configuration
        self.add_vnc_config()

        #self.enable_services()
        self.cleanup()
    #end do_setup

    def run_services(self):
        pdist = platform.dist()[0]
        contrail_openstack = not(getattr(self._args, 'no_contrail_openstack', False))
        if 'database' in self._args.role:
            local("sudo ./contrail_setup_utils/database-server-setup.sh %s" % (self._args.database_listen_ip))
            
        if 'openstack' in self._args.role:
            local("sudo ./contrail_setup_utils/keystone-server-setup.sh")
            local("sudo ./contrail_setup_utils/glance-server-setup.sh")
            local("sudo ./contrail_setup_utils/cinder-server-setup.sh")
            local("sudo ./contrail_setup_utils/nova-server-setup.sh")
            if pdist in ['Ubuntu']:
                self.mysql_svc = 'mysql'
            elif pdist in ['centos', 'redhat']:
               self.mysql_svc = 'mysqld'
            local("service %s restart" % self.mysql_svc)
            local("service supervisor-openstack restart")

        if 'config' in self._args.role:
            keystone_ip = self._args.keystone_ip
            region_name = self._args.region_name
            if self._args.internal_vip:
                # Assumption cfgm and openstack in same node.
                # TO DO: When we introduce contrail_vip for cfgm nodes, this needs to be revisited.
                quantum_ip = self._args.internal_vip
            else:
                quantum_ip = self._args.cfgm_ip
            local("sudo ./contrail_setup_utils/config-server-setup.sh")
            local("sudo ./contrail_setup_utils/quantum-server-setup.sh")
            quant_args = "--ks_server_ip %s --quant_server_ip %s --tenant %s --user %s --password %s --svc_password %s --root_password %s" \
                          %(keystone_ip, quantum_ip, ks_admin_tenant_name, ks_admin_user, ks_admin_password, self.service_token, 
                            env.password)
            if region_name:
                quant_args += " --region_name %s" %(region_name)
            if self._args.manage_neutron:
                local("python /opt/contrail/contrail_installer/contrail_setup_utils/setup-quantum-in-keystone.py %s" %(quant_args))

        if 'collector' in self._args.role:
            if self._args.num_collector_nodes:
                local("sudo ./contrail_setup_utils/collector-server-setup.sh multinode")
            else:
                local("sudo ./contrail_setup_utils/collector-server-setup.sh")

        if 'control' in self._args.role:
            local("sudo ./contrail_setup_utils/control-server-setup.sh")

        if (contrail_openstack and 'compute' in self._args.role):
            if self._fixed_qemu_conf:
                if pdist == 'centos' or pdist == 'fedora' or pdist == 'redhat':
                    local("sudo service libvirtd restart")
                if pdist == 'Ubuntu':
                    local("sudo service libvirt-bin restart")

	# Customized for Workday. 
	# Workday will handle all the nova.conf configuration on the compute node
        if self._args.compute_ip :
            #if contrail_openstack:
                # running compute-server-setup.sh on cfgm sets nova.conf's
                # sql access from ip instead of localhost, causing privilege
                # degradation for nova tables
	
		# Customized for Workday. Path updated to point to contrail setup scripts
                #local("sudo /opt/contrail/contrail_installer/contrail_setup_utils/compute-server-setup.sh")
            #else
                #use contrail specific vif driver
                #local('openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_vif_driver nova_contrail_vif.contrailvif.VRouterVIFDriver')
                # Use noopdriver for firewall
                #local('openstack-config --set /etc/nova/nova.conf DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver')
                #network_api = 'quantum'
                #with(open('/etc/nova/nova.conf', 'r+')) as nova_conf:
                #    if 'neutron_url' in nova_conf.read():
                #        network_api = 'neutron'
                #local('openstack-config --set /etc/nova/nova.conf DEFAULT %s_connection_host %s' % (network_api, self._args.cfgm_ip))
                #local('openstack-config --set /etc/nova/nova.conf DEFAULT %s_url http://%s:9696' % (network_api, self._args.cfgm_ip))
                #local('openstack-config --set /etc/nova/nova.conf DEFAULT %s_admin_password %s' % (network_api, self._args.service_token))
       	     
       		for svc in ['openstack-nova-compute', 'supervisor-vrouter']:
			local('chkconfig %s on' % svc)

        if 'webui' in self._args.role:
            local("sudo ./contrail_setup_utils/webui-server-setup.sh")

        if 'storage' in self._args.role:
            if self._args.nfs_live_migration == 'enabled':
                # Live migration NFS Configurations
                # Setup VM NFS services

                nfs_live_migration_enabled = self._args.nfs_live_migration
                nfs_live_migration_subnet = self._args.nfs_livem_subnet
                nfs_live_migration_image = self._args.nfs_livem_image
                nfs_live_migration_host = self._args.nfs_livem_host

                if nfs_live_migration_enabled == 'enabled':
                    storage_setup_args = " --storage-master %s" %(self._args.storage_master)
                    storage_setup_args = storage_setup_args + " --storage-setup-mode %s" % (self._args.storage_setup_mode)    
                    storage_setup_args = storage_setup_args + " --storage-hostnames %s" %(' '.join(self._args.storage_hostnames))    
                    storage_setup_args = storage_setup_args + " --storage-hosts %s" %(' '.join(self._args.storage_hosts))    
                    storage_setup_args = storage_setup_args + " --storage-host-tokens %s" %(' '.join(self._args.storage_host_tokens))    
                    storage_setup_args = storage_setup_args + " --nfs-livem-subnet %s" %(' '.join(self._args.nfs_livem_subnet))    
                    storage_setup_args = storage_setup_args + " --nfs-livem-image %s" %(' '.join(self._args.nfs_livem_image))    
                    storage_setup_args = storage_setup_args + " --nfs-livem-host %s" %(' '.join(self._args.nfs_livem_host))    
                    with settings(host_string=self._args.storage_master):
                        run("python /opt/contrail/contrail_installer/contrail_setup_utils/livemnfs-ceph-setup.py %s" %(storage_setup_args))
            else:
                # Storage Configurations
                # Setup Ceph services
                storage_setup_args = " --storage-master %s" %(self._args.storage_master)
                storage_setup_args = storage_setup_args + " --storage-setup-mode %s" % (self._args.storage_setup_mode)    
                if self._args.add_storage_node:
                    storage_setup_args = storage_setup_args + " --add-storage-node %s" % (self._args.add_storage_node)    
                storage_setup_args = storage_setup_args + " --storage-hostnames %s" %(' '.join(self._args.storage_hostnames))    
                storage_setup_args = storage_setup_args + " --storage-hosts %s" %(' '.join(self._args.storage_hosts))    
                storage_setup_args = storage_setup_args + " --storage-host-tokens %s" %(' '.join(self._args.storage_host_tokens))    
                storage_setup_args = storage_setup_args + " --storage-disk-config %s" %(' '.join(self._args.storage_disk_config))    
                storage_setup_args = storage_setup_args + " --storage-ssd-disk-config %s" %(' '.join(self._args.storage_ssd_disk_config))    
                storage_setup_args = storage_setup_args + " --storage-journal-config %s" %(' '.join(self._args.storage_journal_config))    
                storage_setup_args = storage_setup_args + " --storage-local-disk-config %s" %(' '.join(self._args.storage_local_disk_config))    
                storage_setup_args = storage_setup_args + " --storage-local-ssd-disk-config %s" %(' '.join(self._args.storage_local_ssd_disk_config))    
                storage_setup_args = storage_setup_args + " --storage-nfs-disk-config %s" %(' '.join(self._args.storage_nfs_disk_config))    
                storage_setup_args = storage_setup_args + " --storage-directory-config %s" %(' '.join(self._args.storage_directory_config))    
                with settings(host_string=self._args.storage_master):
                    run("python /opt/contrail/contrail_installer/contrail_setup_utils/storage-ceph-setup.py %s" %(storage_setup_args))

                # Setup Live migration services
                live_migration_status = self._args.live_migration
                if live_migration_status == 'enabled':
                    storage_setup_args = " --storage-master %s" %(self._args.storage_master)
                    storage_setup_args = storage_setup_args + " --storage-setup-mode %s" % (self._args.storage_setup_mode)    
                    storage_setup_args = storage_setup_args + " --storage-hostnames %s" %(' '.join(self._args.storage_hostnames))    
                    storage_setup_args = storage_setup_args + " --storage-hosts %s" %(' '.join(self._args.storage_hosts))    
                    storage_setup_args = storage_setup_args + " --storage-host-tokens %s" %(' '.join(self._args.storage_host_tokens))    
                    if self._args.add_storage_node:
                        storage_setup_args = storage_setup_args + " --add-storage-node %s" % (self._args.add_storage_node)    
                    with settings(host_string=self._args.storage_master):
                        run("python /opt/contrail/contrail_installer/contrail_setup_utils/compute-live-migration-setup.py %s" %(storage_setup_args))


    #end run_services

#end class Setup


class KeepalivedSetup(Setup):
    def fixup_config_files(self):
        if 'openstack' in self._args.role:
            self_ip = self._args.openstack_ip
            self_index = self._args.openstack_index
        elif 'cfgm' in self._args.role:
            self_ip = self._args.cfgm_ip
            self_index = self._args.cfgm_index

        vip_for_ips = [(self._args.internal_vip, self_ip, 'INTERNAL')]
        if self._args.external_vip:
            vip_for_ips.append((self._args.external_vip, self._args.mgmt_self_ip, 'EXTERNAL'))
        for vip, ip, vip_name in vip_for_ips:
            # keepalived.conf
            device = self.get_device_by_ip(ip)
            netmask = netifaces.ifaddresses(device)[netifaces.AF_INET][0]['netmask']
            prefix = netaddr.IPNetwork('%s/%s' % (ip, netmask)).prefixlen
            state = 'BACKUP'
            delay = 1
            preempt_delay = 1
            timeout = 1 
            rise = 1
            fall = 1
            garp_master_repeat = 3
            garp_master_refresh = 1
            if self_index == 1:
                state = 'MASTER'
                delay = 5
                preempt_delay = 7
                timeout = 3
                rise = 2 
                fall = 2
            if vip_name == 'INTERNAL':
                router_id = 101
                if 'openstack' in self._args.role:
                    router_id = 100
            else:
                router_id = 201
                if 'openstack' in self._args.role:
                    router_id = 200
            priority = router_id - (self_index - 1)
            if self._args.num_nodes > 2 and self_index == 2:
                state = 'BACKUP'
            vip_str = '_'.join([vip_name] + vip.split('.'))
            template_vals = {'__device__': device,
                             '__router_id__' : router_id,
                             '__state__' : state,
                             '__delay__' : delay,
                             '__garp_master_repeat__' : garp_master_repeat,
                             '__garp_master_refresh__' : garp_master_refresh,
                             '__preempt_delay__' : preempt_delay,
                             '__priority__' : priority,
                             '__virtual_ip__' : vip,
                             '__virtual_ip_mask__' : prefix,
                             '__vip_str__' : vip_str,
                             '__timeout__' : timeout,
                             '__rise__' : rise,
                             '__fall__' : fall,
                            }
            data = self._template_substitute(keepalived_conf_template.template,
                                      template_vals)
            with open(self._temp_dir_name + '/keepalived.conf', 'a+') as fp:
                fp.write(data)
        local("sudo mv %s/keepalived.conf /etc/keepalived/" %(self._temp_dir_name))

    def run_services(self):
        local("service keepalived restart")


class OpenstackGaleraSetup(Setup):
    def fixup_config_files(self):
        with settings(warn_only=True):
            local("service contrail-hamon stop")
            local("service cmon stop")
            local("service mysql stop")
            local("rm -rf /var/lib/mysql/grastate.dat")
            local("rm -rf /var/lib/mysql/galera.cache")
        # fix galera_param
        template_vals = {'__mysql_host__' : self._args.openstack_ip,
                         '__mysql_wsrep_nodes__' :
                         '"' + '" "'.join(self._args.galera_ip_list) + '"'}
        self._template_substitute_write(galera_param_template.template,
                                        template_vals,
                                        self._temp_dir_name + '/galera_param')
        local("sudo mv %s/galera_param /etc/contrail/ha/" % (self._temp_dir_name))

        # fix cmon_param
        template_vals = {'__internal_vip__' : self._args.internal_vip,
                         '__haproxy_dips__' :
                         '"' + '" "'.join(self._args.galera_ip_list) + '"'}
        self._template_substitute_write(cmon_param_template.template,
                                        template_vals,
                                        self._temp_dir_name + '/cmon_param')
        local("sudo mv %s/cmon_param /etc/contrail/ha/" % (self._temp_dir_name))

        local("echo %s > /etc/contrail/galeraid" % self._args.openstack_index)
        pdist = platform.dist()[0]
        if pdist in ['Ubuntu']:
            local("ln -sf /bin/true /sbin/chkconfig")
            self.mysql_svc = 'mysql'
            self.mysql_conf = '/etc/mysql/my.cnf'
            wsrep_conf = '/etc/mysql/conf.d/wsrep.cnf'
            wsrep_conf_file = 'wsrep.cnf'
            wsrep_template = wsrep_conf_template.template
        elif pdist in ['centos', 'redhat']:
            self.mysql_svc = 'mysqld'
            self.mysql_conf = '/etc/my.cnf'
            wsrep_conf = self.mysql_conf
            wsrep_conf_file = 'my.cnf'
            wsrep_template = wsrep_conf_centos_template.template
        self.mysql_token_file = '/etc/contrail/mysql.token'

        self.install_mysql_db()
        if self._args.openstack_index == 1:
            self.create_mysql_token_file()
        else:
            self.get_mysql_token_file()
        self.set_mysql_root_password()
        self.setup_grants()
        self.setup_cron()

        # fixup mysql/wsrep config
        local('sed -i -e "s/bind-address/#bind-address/" %s' % self.mysql_conf)
        local('sed -ibak "s/max_connections.*/max_connections=10000/" %s' % self.mysql_conf)
        local('sed -i -e "s/key_buffer/#key_buffer/" %s' % self.mysql_conf)
        local('sed -i -e "s/max_allowed_packet/#max_allowed_packet/" %s' % self.mysql_conf)
        local('sed -i -e "s/thread_stack/#thread_stack/" %s' % self.mysql_conf)
        local('sed -i -e "s/thread_cache_size/#thread_cache_size/" %s' % self.mysql_conf)
        local('sed -i -e "s/myisam-recover/#myisam-recover/" %s' % self.mysql_conf)
        local('sed -i "/\[mysqld\]/a\lock_wait_timeout=600" %s' % self.mysql_conf)
        local('sed -i "/\[mysqld\]/a\interactive_timeout = 60" %s' % self.mysql_conf)
        local('sed -i "/\[mysqld\]/a\wait_timeout = 60" %s' % self.mysql_conf)
        # FIX for UTF8
        if pdist in ['Ubuntu']:
            sku = local("dpkg -p contrail-install-packages | grep Version: | cut -d'~' -f2", capture=True)
            if sku == 'icehouse':
                local('sed -i "/\[mysqld\]/a\character-set-server = utf8" %s' % self.mysql_conf)
                local('sed -i "/\[mysqld\]/a\init-connect=\'SET NAMES utf8\'" %s' % self.mysql_conf)
                local('sed -i "/\[mysqld\]/a\collation-server = utf8_general_ci" %s' % self.mysql_conf)

        if self._args.openstack_index == 1:
            wsrep_cluster_address= ''
        else:
            wsrep_cluster_address =  (':4567,'.join(self._args.galera_ip_list) + ':4567')
        template_vals = {'__wsrep_nodes__' : wsrep_cluster_address,
                         '__wsrep_node_address__' : self._args.openstack_ip,
                         '__mysql_token__' : self.mysql_token
                        }
        self._template_substitute_write(wsrep_template, template_vals,
                                self._temp_dir_name + '/%s' % wsrep_conf_file)
        local("sudo mv %s/%s %s" % (self._temp_dir_name, wsrep_conf_file,
                                    wsrep_conf))
        if self._args.openstack_index == 1:
            local('sed -ibak "s#wsrep_cluster_address=.*#wsrep_cluster_address=gcomm://#g" %s' % (wsrep_conf))

        # fixup cmon config
        template_vals = {'__mysql_nodes__' : ','.join(self._args.galera_ip_list),
                         '__mysql_node_address__' : self._args.internal_vip,
                        }
        self._template_substitute_write(cmon_conf_template.template, template_vals,
                                        self._temp_dir_name + '/cmon.cnf')
        local("sudo mv %s/cmon.cnf /etc/cmon.cnf" % (self._temp_dir_name))

    def install_mysql_db(self):
        local('chkconfig %s on' % self.mysql_svc)
        local('chown -R mysql:mysql /var/lib/mysql/')
        with settings(warn_only=True):
            install_db = local("service %s restart" % self.mysql_svc).failed
        if install_db:
            local('mysql_install_db --user=mysql --ldata=/var/lib/mysql')
            local("service %s restart" % self.mysql_svc)

    def create_mysql_token_file(self):
        # Use MYSQL_ROOT_PW from the environment or generate a new password
        if os.path.isfile(self.mysql_token_file):
            self.mysql_token = local('cat %s' % self.mysql_token_file, capture=True).strip()
        else:
            if os.environ.get('MYSQL_ROOT_PW'):
                self.mysql_token = os.environ.get('MYSQL_ROOT_PW')
            else:
                 self.mysql_token = local('openssl rand -hex 10', capture=True).strip()
            local("echo %s > %s" % (self.mysql_token, self.mysql_token_file))
            local("chmod 400 %s" % self.mysql_token_file)

    def get_mysql_token_file(self):
        retries = 10
        if not os.path.isfile(self.mysql_token_file):
            while retries:
                with settings(host_string = 'root@%s' % (self._args.galera_ip_list[0]),
                              password=env.password, warn_only=True):
                    if get('%s' % self.mysql_token_file, '/etc/contrail/').failed:
                        time.sleep(1)
                        retries -= 1
                        print " Retry(%s) to get the %s." % ((5 - retries), self.mysql_token_file)
                    else:
                        break
        self.mysql_token = local('cat %s' % self.mysql_token_file, capture=True).strip()

    def set_mysql_root_password(self):
        # Only for the very first time 
        mysql_priv_access = "mysql -uroot -e"
        # Set root password for mysql
        with settings(warn_only=True):
            if local('echo show databases |mysql -u root > /dev/null').succeeded:
                local('%s "use mysql; update user set password=password(\'%s\') where user=\'root\'"' % (mysql_priv_access, self.mysql_token))
                local('mysqladmin password %s' % self.mysql_token)
            elif local('echo show databases |mysql -u root -p%s> /dev/null' % self.mysql_token).succeeded:
                print "Mysql root password is already set to '%s'" % self.mysql_token
            else:
                raise RuntimeError("MySQL root password unknown, reset and retry")
                
    def setup_grants(self):
        mysql_cmd =  "mysql --defaults-file=%s -uroot -p%s -e" % (self.mysql_conf, self.mysql_token)
        host_list = self._args.galera_ip_list + ['localhost', '127.0.0.1']
        for host in host_list:
            with settings(hide('everything'),warn_only=True):
                 local('mysql -u root -p%s -e "CREATE USER \'root\'@\'%s\' IDENTIFIED BY %s"' % (self.mysql_token, host, self.mysql_token))
            local('%s "SET WSREP_ON=0;SET SQL_LOG_BIN=0; GRANT ALL ON *.* TO root@%s IDENTIFIED BY \'%s\'"' %
                   (mysql_cmd, host, self.mysql_token))
        local('%s "SET wsrep_on=OFF; DELETE FROM mysql.user WHERE user=\'\'"' % mysql_cmd)
        local('%s "FLUSH PRIVILEGES"' % mysql_cmd)

    def setup_cron(self):
        with settings(hide('everything'), warn_only=True):
            local('crontab -l > %s/galera_cron' % self._temp_dir_name)
        local('echo "0 0 * * * /opt/contrail/bin/contrail-token-clean.sh" >> %s/galera_cron' % self._temp_dir_name)
        local('crontab %s/galera_cron' % self._temp_dir_name)
        local('rm %s/galera_cron' % self._temp_dir_name)

    def run_services(self):
        if self._args.openstack_index == 1:
            local("service %s restart" % self.mysql_svc)
        else:
            cmd = "mysql -h%s -uroot -p%s " % (self._args.galera_ip_list[0], self.mysql_token)
            cmd += "-e \"show global status where variable_name='wsrep_local_state'\" | awk '{print $2}' | sed '1d'"
            for i in range(10):
                wsrep_local_state = local(cmd, capture=True).strip()
                if wsrep_local_state == '4':
                    break
                else:
                    time.sleep(2)
                    print "Waiting for first galera node to create new cluster."
            if wsrep_local_state != '4':
                raise RuntimeError("Unable able to bring up galera in first node, please verify and continue.")
            local("service %s restart" % self.mysql_svc)
        local("sudo update-rc.d -f mysql remove")
        local("sudo update-rc.d mysql defaults")


def main(args_str = None):
    setup_obj = Setup(args_str)
    setup_obj.do_setup()
#end main

if __name__ == "__main__":
    main()
