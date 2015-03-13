import string

template = string.Template("""
[global]
;WEB_SERVER = 127.0.0.1
;WEB_PORT = 9696  ; connection through quantum plugin

WEB_SERVER = 127.0.0.1
WEB_PORT = 8082 ; connection to api-server directly
BASE_URL = /
;BASE_URL = /tenants/infra ; common-prefix for all URLs

; Authentication settings (optional)
[auth]
AUTHN_TYPE = keystone
AUTHN_PROTOCOL =$__contrail_ks_auth_protocol__
AUTHN_SERVER=$__contrail_keystone_ip__
AUTHN_PORT = 35357
AUTHN_URL = /v2.0/tokens
insecure=$__keystone_insecure_flag__
""")

