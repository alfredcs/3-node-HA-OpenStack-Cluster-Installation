import string

template = string.Template("""
test:test
test2:test2
test3:test3
api-server:$__api_server__
schema-transformer:$__schema_transformer__
svc-monitor:$__svc_monitor__
control-user:$__control_user_passwd__
control-node-1:control-node-1
control-node-2:control-node-2
control-node-3:control-node-3
control-node-4:control-node-4
control-node-5:control-node-5
control-node-6:control-node-6
control-node-7:control-node-7
control-node-8:control-node-8
control-node-9:control-node-9
control-node-10:control-node-10
dhcp:dhcp
dns-user:$__dns_user_passwd__
visual:visual
sensor:sensor

# compliance testsuite users
mapclient:mapclient
helper:mapclient

# This is a read-only MAPC
reader:reader
""")
