#!/usr/bin/env python
import sys
import os
import ConfigParser
#import argparse
from keystoneclient.v2_0 import client
from keystoneclient import exceptions
#from glance import client as glanceclient
#from glance.common import exception
#from glance.common import utils
#from glance import version


STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3
conf_file=None
default_region_name="regionOne"
default_token="None"
default_admin_port=35357
default_admin_password="None"
default_admin_user="Nova"
default_admin_tenant_name="service"
default_auth_url="https://127.0.0.1:"

def _read_cfg(cfg_parser, section, option, default):
        try:
            val = cfg_parser.get(section, option)
        except (AttributeError,
                ConfigParser.NoOptionError,
                ConfigParser.NoSectionError):
            val = default

        return val
#end _read_cfg

cfg_parser = ConfigParser.ConfigParser()
clen = len(cfg_parser.read(conf_file or  "/etc/keystone/keystone.conf"))
admin_port=_read_cfg(cfg_parser, 'DEFAULT', 'admin_port', default_admin_port)
clen_nova = len(cfg_parser.read(conf_file or  "/etc/nova/nova.conf"))

try:
    c = client.Client(username=_read_cfg(cfg_parser, 'keystone_authtoken', 'admin_user', default_admin_user),
                  tenant_name=_read_cfg(cfg_parser, 'keystone_authtoken', 'admin_tenant_name', default_admin_tenant_name),
                  password=_read_cfg(cfg_parser, 'keystone_authtoken', 'admin_password', default_admin_password),
                  auth_url=default_auth_url+admin_port+"/v2.0",
		  insecure=True,
                  region_name=_read_cfg(cfg_parser, 'DEFAULT', 'region', default_region_name))
    if not c.authenticate():
        raise Exception("Authentication failed")
#    if not args.no_admin:
    if not c.tenants.list():
        raise Exception("Tenant list is empty")
except Exception as e:
    print "HTTP/1.1 503 Service Unavailable"
    print "Content-Type: Content-Type: text/plain"
    print
    print str(e)
    sys.exit(STATE_CRITICAL)

msgs = []
endpoints = c.service_catalog.get_endpoints()
#services = args.services or endpoints.keys()
services = endpoints.keys()
for service in services:
    if not service in endpoints.keys():
        msgs.append("`%s' service is missing" % service)
        continue

    if not len(endpoints[service]):
        msgs.append("`%s' service is empty" % service)
        continue

    if not len(endpoints[service]):
        msgs.append("`%s' service is empty" % service)
        continue

    if not any([ "publicURL" in endpoint.keys() for endpoint in endpoints[service] ]):
        msgs.append("`%s' service has no publicURL" % service)

if msgs:
    print ", ".join(msgs)
    print "HTTP/1.1 503 Service Unavailable"
    sys.exit(STATE_WARNING)

#print "Got token %s for user %s and tenant %s with management URL %s" % (c.auth_token, c.auth_user_id, c.auth_tenant_id, c.management_url)
print "HTTP/1.1 200 OK"
print "Content-Type: Content-Type: text/plain"
print
print "Keystone checked!"
KEYSTONE_OK=1
