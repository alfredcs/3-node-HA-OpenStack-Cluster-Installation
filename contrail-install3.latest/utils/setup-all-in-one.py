#!/usr/bin/python

import sys
import socket
import os
import time

#get IP to use for configuration
ip = socket.gethostbyname(socket.gethostname())
print '\nIs this your IP to use for configuration: ' + ip 
var = raw_input('Answer [yes/no]: ')
if var != 'yes':
    sys.exit(0)

#set root password
os.environ["PASSWORD"] = "c0ntrail123"

#database setup
cmd = './setup-vnc-database.py --self_ip ' + ip
print '\nDatabase setup \n' + cmd + '\n'
time.sleep(2)
os.system(cmd)

#config setup
cmd = './setup-vnc-cfgm.py --self_ip ' + ip + ' --collector_ip ' + ip + ' --cassandra_ip_list ' + ip
print '\nConfig setup \n' + cmd + '\n'
time.sleep(2)
os.system(cmd)

#collector setup
cmd = './setup-vnc-collector.py --cassandra_ip_list ' + ip
print '\nCollector setup \n' + cmd + '\n'
time.sleep(2)
os.system(cmd)

#webui setup
cmd = './setup-vnc-webui.py --cfgm_ip ' + ip
print '\nWebui setup \n' + cmd + '\n'
time.sleep(2)
os.system(cmd)

#controller setup
cmd = './setup-vnc-control.py --cfgm_ip ' + ip + ' --collector_ip ' + ip + ' --self_ip ' + ip
print '\nController setup \n' + cmd 
time.sleep(2)
os.system(cmd)

#compute/vrouter setup
cmd = './setup-vnc-vrouter.py --cfgm_ip ' + ip + ' --control_1_ip ' + ip + ' --collector_ip ' + ip + ' --self_ip ' + ip
print 'Compute setup \n' + cmd + '\n'
time.sleep(2)
os.system(cmd)
