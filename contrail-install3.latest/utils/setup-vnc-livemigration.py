#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.setup import Setup

class SetupVncStorage(object):
    def __init__(self, args_str = None):
        #print sys.argv[1:]
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        storage_master = self._args.storage_master

        setup_args_str = "--role storage"
        setup_args_str = setup_args_str + " --storage-master %s" % (storage_master) 
        setup_args_str = setup_args_str + " --storage-setup-mode %s" % (self._args.storage_setup_mode)    
        setup_args_str = setup_args_str + " --storage-hostnames %s" %(' '.join(self._args.storage_hostnames))    
        setup_args_str = setup_args_str + " --storage-hosts %s" %(' '.join(self._args.storage_hosts))    
        setup_args_str = setup_args_str + " --storage-host-tokens %s" %(' '.join(self._args.storage_host_tokens))    
        live_migration_status = self._args.live_migration
        setup_args_str = setup_args_str + " --live-migration %s" % (live_migration_status) 
        nfs_live_migration_option = self._args.nfs_live_migration
        setup_args_str = setup_args_str + " --nfs-live-migration %s" % (nfs_live_migration_option) 
        setup_args_str = setup_args_str + " --nfs-livem-subnet %s" % (' '.join(self._args.nfs_livem_subnet))
        setup_args_str = setup_args_str + " --nfs-livem-image %s" % (' '.join(self._args.nfs_livem_image))
        setup_args_str = setup_args_str + " --nfs-livem-host %s" % (' '.join(self._args.nfs_livem_host))


        #Setup storage if storage is defined in testbed.py
        setup_obj = Setup(setup_args_str)
        setup_obj.do_setup()
        setup_obj.run_services()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python setup-vnc-storage.py --storage-master 10.157.43.171 --storage-hostnames cmbu-dt05 cmbu-ixs6-2 --storage-hosts 10.157.43.171 10.157.42.166 --storage-host-tokens n1keenA n1keenA --storage-disk-config 10.157.43.171:sde 10.157.43.171:sdf 10.157.43.171:sdg --storage-directory-config 10.157.42.166:/mnt/osd0 --live-migration enabled
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)
        
        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
            'storage_master': '127.0.0.1',
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

        parser.add_argument("--storage-master", help = "IP Address of storage master node")
        parser.add_argument("--storage-hostnames", help = "Host names of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-hosts", help = "IP Addresses of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-host-tokens", help = "Passwords of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-disk-config", help = "Disk list to be used for distrubuted storage", nargs="+", type=str)
        parser.add_argument("--storage-directory-config", help = "Directories to be sued for distributed storage", nargs="+", type=str)
        parser.add_argument("--live-migration", help = "Live migration enabled")
        parser.add_argument("--nfs-live-migration", help = "NFS for Live migration enabled")
        parser.add_argument("--nfs-livem-subnet", help = "Subnet for the NFS Live migration VM", nargs="+", type=str)
        parser.add_argument("--nfs-livem-image", help = "Image for the NFS Live migration VM", nargs="+", type=str)
        parser.add_argument("--nfs-livem-host", help = "Image for the NFS Live migration VM", nargs="+", type=str)
        parser.add_argument("--storage-setup-mode", help = "Storage configuration mode")

        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupVncStorage

def main(args_str = None):
    SetupVncStorage(args_str)
#end main

if __name__ == "__main__":
    main() 
