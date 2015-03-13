#!/usr/bin/env python
import sys,os,getopt,re
import ConfigParser
import httplib
from urllib import urlencode

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3
verbose=0
default_listen_ip_addr="127.0.0.1"
default_listen_port="5998"
default_auth_protocol="http"
discovery_conf_file="/etc/contrail/contrail-discovery.conf"

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

def usage(message=None):
  print "Usage: %s [-h] [-f|--file <config_file>]" % (sys.argv[0])
  print "-h|--help: show this message"
  print "-v|--verbose: include details in output"
  print "-f|--file: dir and filename of the contrail discovery config file"
  sys.exit(-1)

# end of _get_keystone_token

# --- main()a ---

(opts, args) = getopt.getopt(sys.argv[1:], "f:hv", ["Contrail API config file", "help", "verbose"]) 
for o, a in opts:
  if o in ["-h", "--help"]:
	usage()
  elif o in ["-f", "--file"]:
	discovery_conf_file=a
  elif o in ["-v", "--verbose"]:
        verbose=1

cfg_parser_contrail = ConfigParser.ConfigParser()
clen_contrail = len(cfg_parser_contrail.read(discovery_conf_file))
listen_port=_read_cfg(cfg_parser_contrail, 'DEFAULT', 'listen_port', default_listen_port)
listen_ip_addr=_read_cfg(cfg_parser_contrail, 'DEFAULT', 'listen_ip_addr', default_listen_ip_addr)

headers = { "Content-Type": "application/json" }
params=urlencode({})
conn = httplib.HTTPConnection(listen_ip_addr, port=listen_port, timeout=2)

try:
    action_str="/services"
    #import pdb;pdb.set_trace()
    conn.request("GET", action_str, params, headers)
    response = conn.getresponse().read()
    if not response:
        raise Exception("Query discovery failed. No response")
    elif '503' in response.lower() or re.search('unavailable', response, re.IGNORECASE):
	raise Exception("Query discovery failed. Service unavailable")
    else:
	print "HTTP/1.1 200 OK"
	print "Content-Type: Content-Type: text/plain"
	if (verbose > 0 ):
		print
		print response
	print
	print "Discovery API checked!"
    	sys.exit(STATE_OK)
except Exception as e:
    print "HTTP/1.1 503 Service Unavailable"
    print "Content-Type: Content-Type: text/plain"
    print
    print "<html><body><h1>503 Discovery API Service Unavailable</h1></body></html>"
    print str(e)
    print "Discovery API failed!"
    sys.exit(STATE_CRITICAL)
