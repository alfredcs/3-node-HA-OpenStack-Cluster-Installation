import string

template = string.Template("""#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#
# Control-node configuration options
#

[DEFAULT]
  analytics_data_ttl=$__contrail_analytics_data_ttl__
  cassandra_server_list=$__contrail_cassandra_server_list__
# dup=0
  hostip=$__contrail_host_ip__ # Resolved IP of `hostname`
# hostname= # Retrieved as `hostname`
  http_server_port=$__contrail_http_server_port__
# log_category=
# log_disable=0
  log_file=$__contrail_log_file__
# log_files_count=10
# log_file_size=1048576 # 1MB
# log_level=SYS_NOTICE
# log_local=0
  syslog_port=$__contrail_analytics_syslog_port__
# test_mode=0

[COLLECTOR]
  port=$__contrail_listen_port__
# server= 0.0.0.0

[DISCOVERY]
# port=5998
  server=$__contrail_discovery_ip__ # discovery_server IP address

[REDIS]
  port=6379
  server=127.0.0.1

""")
