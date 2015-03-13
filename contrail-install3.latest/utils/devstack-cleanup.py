#!/usr/bin/python

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


class DevstackCleanup(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        with settings(warn_only = True):
            with lcd("/home/stack/devstack"):
                local("./unstack.sh")
        
            local("sudo rm -rf /home/stack/devstack")
            local("sudo yum remove -y mysql-libs")
            local("sudo rm -rf /var/lib/mysql/")
            local("sudo rm -rf /var/lib/zookeeper/")
            local("sudo rm -rf /opt/stack/")
            local("sudo rm -rf /opt/contrail/")
            local("sudo rm -rf /etc/init.d/contrail")
            local("sudo rm -rf /etc/rc.d/init.d/contrail")
            local("sudo rm -rf /home/stack/keystone-signing")
            local("sudo rm /etc/httpd/conf.d/horizon.conf")

            local("sudo rm -rf /etc/nova/")
            local("sudo rm -rf /etc/quantum/")
            local("sudo rm -rf /etc/glance/")
            local("sudo rm -rf /etc/cinder/")
            local("sudo rm -rf /etc/keystone/")

            local("sudo rm -rf /var/log/nova/")
            local("sudo rm -rf /var/log/quantum/")
            local("sudo rm -rf /var/log/glance/")
            local("sudo rm -rf /var/log/cinder/")
            local("sudo rm -rf /var/log/keystone/")

            local("sudo rm -rf /usr/lib/python2.7/site-packages/*nova*/")
            local("sudo rm -rf /usr/lib/python2.7/site-packages/*quantum*/")
            local("sudo rm -rf /usr/lib/python2.7/site-packages/*glance*/")
            local("sudo rm -rf /usr/lib/python2.7/site-packages/*cinder*/")
            local("sudo rm -rf /usr/lib/python2.7/site-packages/*keystone*/")

            result = local("sudo ls /etc/libvirt/qemu/instance*.xml | cut -d '/' -f 5 | cut -d '.' -f 1", capture = True)
            for inst_name in result.split():
                with settings(warn_only = True):
                    sudo('virsh destroy %s' %(inst_name))
                    sudo('virsh undefine %s' %(inst_name))
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python devstack-cleanup.py
        '''

        return

#end class DevstackCleanup

def main(args_str = None):
    DevstackCleanup(args_str)
#end main

if __name__ == "__main__":
    main()
