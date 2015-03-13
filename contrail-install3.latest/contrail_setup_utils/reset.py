import argparse
import ConfigParser

import os
import sys
import time
import re
import string
import socket

import subprocess

import json
from pprint import pformat

import tempfile
import platform

dist = platform.dist()[0]
if  dist == 'centos':
    subprocess.call("sudo pip-python install contrail_setup_utils/pycrypto-2.6.tar.gz", shell=True)
    subprocess.call("sudo pip-python install contrail_setup_utils/paramiko-1.11.0.tar.gz", shell=True)
    subprocess.call("sudo pip-python install contrail_setup_utils/Fabric-1.7.0.tar.gz", shell=True)
    subprocess.call("sudo pip-python install contrail_setup_utils/zope.interface-3.7.0.tar.gz", shell=True)

from fabric.api import local
from fabric.operations import get, put
from fabric.context_managers import lcd, settings


class Reset(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        self._reset_tgt_path = os.path.abspath(os.path.dirname(sys.argv[0]))

        self._temp_dir_name = tempfile.mkdtemp()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python reset.py --role control --role compute
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

        all_defaults = {'global': global_defaults,
                       }
        parser.set_defaults(**all_defaults)

        parser.add_argument("--role", action = 'append', 
                            help = "Role of server (config, control, compute, collector, webui, database")
    
        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

    def cleanup(self):
        os.removedirs(self._temp_dir_name)
    #end cleanup

    def disable_services(self):
        if 'config' in self._args.role:
            local("sudo ./contrail_setup_utils/config-server-cleanup.sh")

        if 'collector' in self._args.role:
            local("sudo ./contrail_setup_utils/collector-server-cleanup.sh")

        if 'control' in self._args.role:
            local("sudo ./contrail_setup_utils/control-server-cleanup.sh")

        if 'compute' in self._args.role and 'config' not in self._args.role:
            local("sudo ./contrail_setup_utils/compute-server-cleanup.sh")

        if 'webui' in self._args.role:
            local("sudo ./contrail_setup_utils/webui-server-cleanup.sh")
            
        if 'database' in self._args.role:
            local("sudo ./contrail_setup_utils/database-server-cleanup.sh")    

    #end disable_services

    def remove_packages(self):
        pkgs_out = local("yum list installed | grep contrail_demo_repo | awk '{ print $1 }'",
                         capture = True)

        for pkg_name in pkgs_out.split():
            if re.match('vnagent', pkg_name):
                continue

            local("sudo yum remove -y %s" %(pkg_name))

    #end remove_packages

    def remove_repo(self):
        local("sudo rm /etc/yum.repos.d/contrail_fedora.repo")
        local("sudo rm /etc/yum.repos.d/contrail_demo.repo")
    #end remove_repo

    def cleanup(self):
        os.removedirs(self._temp_dir_name)
    #end cleanup

    def do_reset(self):
        self.disable_services()
        #self.remove_packages()
        #self.remove_repo()
        self.cleanup()
    #end do_reset

#class Reset
