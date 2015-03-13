import string

template = string.Template("""#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#
# Query-Engine configuration options
#

[DEFAULT]
# analytics_data_ttl=48
  cassandra_server_list=$__contrail_cassandra_server_list__
  collectors=$__contrail_collector__:$__contrail_collector_port__
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
# test_mode=0

[DISCOVERY]
# port=5998
# server= # discovery_server IP address

[REDIS]
  port=$__contrail_redis_server_port__
  server=$__contrail_redis_server__

""")
