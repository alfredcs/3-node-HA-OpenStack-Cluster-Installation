#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys

sys.path.insert(0, os.getcwd())
from contrail_setup_utils.reset import Reset

class ResetVncVrouter(object):
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        reset_args_str = "--role compute"
        reset_obj = Reset(reset_args_str)
        reset_obj.do_reset()
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python reset-vnc-vrouter.py
        '''
        pass
    #end _parse_args

#end class ResetVncVrouter

def main(args_str = None):
    ResetVncVrouter(args_str)
#end main

if __name__ == "__main__":
    main()
