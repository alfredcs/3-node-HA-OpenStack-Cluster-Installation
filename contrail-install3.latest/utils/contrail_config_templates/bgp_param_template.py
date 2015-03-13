import string

template = string.Template("""#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#
# Control-node configuration options
#

[DEFAULT]
# bgp_config_file=bgp_config.xml
# bgp_port=179
# collectors= # Provided by discovery server
  hostip=$__contrail_host_ip__ # Resolved IP of `hostname`
  hostname=$__contrail_hostname__ # Retrieved as `hostname`
# http_server_port=8083
# log_category=
# log_disable=0
  log_file=/var/log/contrail/contrail-control.log
# log_files_count=10
# log_file_size=10485760 # 10MB
# log_level=SYS_NOTICE
# log_local=0
# test_mode=0
# xmpp_server_port=5269

[DISCOVERY]
# port=5998
  server=$__contrail_discovery_ip__ # discovery-server IP address

[IFMAP]
  certs_store=$__contrail_cert_ops__
  password=$__contrail_ifmap_paswd__
# server_url= # Provided by discovery server, e.g. https://127.0.0.1:8443
  user=$__contrail_ifmap_usr__

""")
