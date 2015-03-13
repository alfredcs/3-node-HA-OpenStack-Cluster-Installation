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
default_token=""
default_bind_port=9292
headers = { "Content-Type": "application/json" }
params=urlencode({})

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
clen = len(cfg_parser.read(conf_file or  "/etc/glance/glance-api.conf"))
bind_port=_read_cfg(cfg_parser, 'DEFAULT', 'bind_port', default_bind_port)
conn = httplib.HTTPConnection("127.0.0.1", port=bind_port, timeout=2)

try:
    conn.request("GET", "/v2/images/detail", params, headers)
    response = conn.getresponse()
    if not response.read():
        raise Exception("Query images failed")
except Exception as e:
    print "HTTP/1.1 503 Service Unavailable"
    print "Content-Type: Content-Type: text/plain"
    print
    print str(e)
    sys.exit(STATE_CRITICAL)

print "HTTP/1.1 200 OK"
print "Content-Type: Content-Type: text/plain"
print
print "Glance API checked!"
GLANCE_API_OK=1
