#!/usr/bin/env python
import sys, os, getopt
import ConfigParser
import httplib
from urllib import urlencode

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3
conf_file=None
default_region_name="regionOne"
default_bind_port="9696"
default_admin_password="None"
default_admin_user="neutron"
default_admin_tenant_name="service"
default_auth_host="127.0.0.1"
default_auth_port="35357"
default_auth_protocol="http"
default_insecure="False"
auth_token_nneutron=""
neutron_conf_file="/etc/neutron/neutron.conf"
verbose=0

def _read_cfg(cfg_parser, section, option, default):
        try:
            val = cfg_parser.get(section, option)
        except (AttributeError,
                ConfigParser.NoOptionError,
                ConfigParser.NoSectionError):
            val = default

        return val
#end _read_cfg

def _get_keystone_token(admin_user, admin_tenant_name, admin_password, auth_protocol, auth_host, auth_port, insecure, region_name):
        from keystoneclient.v2_0 import client
        from keystoneclient import exceptions
        token_id=[]
        try:
                c_keystone = client.Client(username=admin_user, tenant_name=admin_tenant_name, password=admin_password,
                        auth_url=auth_protocol+"://"+auth_host+":"+auth_port+"/v2.0", insecure=insecure, region_name=region_name)
                if not c_keystone.authenticate():
                        raise Exception("Authentication failed")
        except Exception as e:
                print str(e)
                sys.exit(STATE_CRITICAL)
        token_id.append(c_keystone.auth_token)
        token_id.append(c_keystone.tenant_id)

        return token_id

# end of _get_keystone_token

def usage(message=None):
  print "Usage: %s [-h] [-f|--file <config_file>]" % (sys.argv[0])
  print "-h|--help: show this message"
  print "-v|--verbose: include details in output"
  print "-f|--file: dir and filename of the neutron config file"
  sys.exit(-1)



(opts, args) = getopt.getopt(sys.argv[1:], "f:hv", ["Neutron config file", "help", "verbose"])
for o, a in opts:
  if o in ["-h", "--help"]:
        usage()
  elif o in ["-f", "--file"]:
        neutron_conf_file=a
  elif o in ["-v", "--verbose"]:
        verbose=1

#import pdb; pdb.set_trace()
conf_file_neutron=None
cfg_parser_neutron = ConfigParser.ConfigParser()
clen_neutron = len(cfg_parser_neutron.read(conf_file_neutron or  neutron_conf_file))
auth_port=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'auth_port', default_auth_port)
auth_protocol=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'auth_protocol', default_auth_protocol)
auth_host=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'auth_host', default_auth_host)
admin_user=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'admin_user', default_admin_user)
admin_password=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'admin_password', default_admin_password)
admin_tenant_name=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'admin_tenant_name', default_admin_tenant_name)
insecure=_read_cfg(cfg_parser_neutron, 'keystone_authtoken', 'insecure', default_insecure)
bind_port=_read_cfg(cfg_parser_neutron, 'DEFAULT', 'bind_port', default_bind_port)
region_name=_read_cfg(cfg_parser_neutron, 'DEFAULT', 'region', default_region_name)

auth_token_id_neutron=_get_keystone_token(admin_user, admin_tenant_name, admin_password, auth_protocol, auth_host, auth_port, insecure, region_name)
headers = { "X-Auth-Project-Id": admin_tenant_name, "Content-Type": "application/json", "X-Auth-Token": auth_token_id_neutron[0] }
params=urlencode({})
conn = httplib.HTTPConnection("127.0.0.1", port=bind_port, timeout=2)
action_str="/v2.0/networks"

try:
    conn.request("GET", action_str, params, headers)
    response = conn.getresponse().read()
    if not response:
        raise Exception("Query Neutron API failed. No response!")
    elif '503' in response or 'unavailable' in response.lower():
	raise Exception("Query Neutron API failed. Service Unavailable!")
    else:
	print "HTTP/1.1 200 OK"
	print "Content-Type: Content-Type: text/plain"
	if ( verbose > 0 ):
		print
		print response
	print
	print "Neutron API checked!"
    	sys.exit(STATE_OK)
except Exception as e:
    print "HTTP/1.1 503 Service Unavailable"
    print "Content-Type: Content-Type: text/plain"
    print
    print str(e)
    print "Neutron API failed!"
    sys.exit(STATE_CRITICAL)
