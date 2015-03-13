#!/usr/bin/env python
import sys
import os
import ConfigParser
import httplib
from urllib import urlencode

STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3
conf_file=None
default_region_name="regionOne"
default_token="None"
default_osapi_compute_listen_port="8774"
default_admin_password="None"
default_admin_user="Nova"
default_admin_tenant_name="service"
default_auth_host="127.0.0.1"
default_auth_port="35357"
default_auth_protocol="http"
auth_token_nova=""

def _read_cfg(cfg_parser, section, option, default):
        try:
            val = cfg_parser.get(section, option)
        except (AttributeError,
                ConfigParser.NoOptionError,
                ConfigParser.NoSectionError):
            val = default

        return val
#end _read_cfg
def _get_keystone_token():
	from keystoneclient.v2_0 import client
	from keystoneclient import exceptions
	import ConfigParser
	STATE_OK = 0
	STATE_WARNING = 1
	STATE_CRITICAL = 2
	STATE_UNKNOWN = 3
	token_id=[]
	conf_file_keystone=None
	default_region_name="regionOne"
	default_token="None"
	default_admin_port=35357
	default_admin_password="None"
	default_admin_user="Nova"
	default_admin_tenant_name="service"
	default_auth_url="https://127.0.0.1:"
	cfg_parser_keystone = ConfigParser.ConfigParser()
	clen_keystone = len(cfg_parser_keystone.read(conf_file_keystone or  "/etc/keystone/keystone.conf"))
	admin_port=_read_cfg(cfg_parser_keystone, 'DEFAULT', 'admin_port', default_admin_port)
	clen_nova = len(cfg_parser_keystone.read(conf_file or  "/etc/nova/nova.conf"))
	try:
    		c_keystone = client.Client(username=_read_cfg(cfg_parser_keystone, 'keystone_authtoken', 'admin_user', default_admin_user),
                  	tenant_name=_read_cfg(cfg_parser_keystone, 'keystone_authtoken', 'admin_tenant_name', default_admin_tenant_name),
                  	password=_read_cfg(cfg_parser_keystone, 'keystone_authtoken', 'admin_password', default_admin_password),
                  	auth_url=default_auth_url+admin_port+"/v2.0",
                  	insecure=True,
                  	region_name=_read_cfg(cfg_parser_keystone, 'DEFAULT', 'region', default_region_name))
    		if not c_keystone.authenticate():
        		raise Exception("Authentication failed")
	except Exception as e:
    		print str(e)
    		sys.exit(STATE_CRITICAL)
	token_id.append(c_keystone.auth_token)
	token_id.append(c_keystone.tenant_id)

	return token_id

# end of _get_keystone_token


#import pdb; pdb.set_trace()
cfg_parser = ConfigParser.ConfigParser()
clen = len(cfg_parser.read(conf_file or  "/etc/nova/nova.conf"))
osapi_compute_listen_port=_read_cfg(cfg_parser, 'DEFAULT', 'osapi_compute_listen_port', default_osapi_compute_listen_port)
auth_protocol=_read_cfg(cfg_parser, 'keystone_authtoken', 'auth_protocol', default_auth_protocol)
auth_token_id_nova=_get_keystone_token()
project_id=_read_cfg(cfg_parser, 'keystone_authtoken', 'admin_tenant_name', default_admin_tenant_name)
headers = { "X-Auth-Project-Id": project_id, "Content-Type": "application/json", "X-Auth-Token": auth_token_id_nova[0] }
params=urlencode({})
conn = httplib.HTTPConnection("127.0.0.1", port=osapi_compute_listen_port, timeout=2)
action_str="/v2/"+auth_token_id_nova[1]+"/servers/detail"

try:
    conn.request("GET", action_str, params, headers)
    response = conn.getresponse()
    if not response.read():
        raise Exception("Query images failed")
except Exception as e:
    print "HTTP/1.1 503 Service Unavailable"
    print "Content-Type: Content-Type: text/plain"
    print
    print str(e)
    sys.exit(STATE_CRITICAL)

#print "Got token %s for user %s and tenant %s with management URL %s" % (c.auth_token, c.auth_user_id, c.auth_tenant_id, c.management_url)
print "HTTP/1.1 200 OK"
print "Content-Type: Content-Type: text/plain"
print
print "Nova API checked!"
