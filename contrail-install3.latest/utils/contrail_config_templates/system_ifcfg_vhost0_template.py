import string

template = string.Template("""
#Contrail vhost0
DEVICE=vhost0
ONBOOT=yes
BOOTPROTO=none
IPV6INIT=no
USERCTL=yes
IPADDR=$__contrail_host_ip__
NETMASK=$__contrail_host_netmask__
PREFIX=$__contrail_host_prefixlen__
GATEWAY=$__contrail_host_gateway__
DNS1=$__contrail_cfg_dns1__
DNS2=$__contrail_cfg_dns2__
""")
