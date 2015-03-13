import string

template = string.Template("""
[DEFAULTS]
host_ip = $__contrail_host_ip__
cassandra_server_list=$__contrail_cassandra_server_list__
collectors = $__contrail_collector__:$__contrail_collector_port__
http_server_port = $__contrail_http_server_port__
rest_api_port = $__contrail_rest_api_port__
rest_api_ip = 0.0.0.0 
log_local = $__contrail_log_local__
log_level = $__contrail_log_level__
log_category = $__contrail_log_category__
log_file = $__contrail_log_file__

[DISCOVERY]
disc_server_ip = $__contrail_discovery_ip__
disc_server_port = $__contrail_discovery_port__

[REDIS]
redis_server_port = $__contrail_redis_server_port__
redis_query_port = $__contrail_redis_query_port__

""")
