import string

template = string.Template("""
# This file contains wsrep-related mysqld options. It should be included
# in the main MySQL configuration file.
#
# Options that need to be customized:
#  - wsrep_provider
#  - wsrep_cluster_address
#  - wsrep_sst_auth
# The rest of defaults should work out of the box.

##
## mysqld options _MANDATORY_ for correct opration of the cluster
##
[mysqld]

# (This must be substituted by wsrep_format)
binlog_format=ROW

# Currently only InnoDB storage engine is supported
default-storage-engine=innodb

# to avoid issues with 'bulk mode inserts' using autoinc
innodb_autoinc_lock_mode=2

# This is a must for paralell applying
innodb_locks_unsafe_for_binlog=1
#INNODB
default-storage-engine=innodb
engine-condition-pushdown=1
innodb_stats_on_metadata=0
innodb_autoinc_lock_mode=2
innodb_locks_unsafe_for_binlog=1
innodb_flush_method=O_DIRECT
innodb_thread_concurrency=0
innodb_doublewrite=1
innodb_io_capacity=2000
innodb_write_io_threads=40
innodb_read_io_threads=40
innodb_file_per_table=1
innodb_flush_log_at_trx_commit=2
innodb_additional_mem_pool_size=1000M
innodb_buffer_pool_size=1G
innodb_rollback_on_timeout=ON
innodb_lock_wait_timeout=10

#BUFFERS
lower_case_table_names=0
table_open_cache=1024
thread_cache_size=512
sysdate-is-now=1
memlock=0
skip-name-resolve
max_allowed_packet = 512M
max_heap_table_size = 64M
tmp_table_size = 64M
key_buffer_size = 24M

# Query Cache is not supported with wsrep
#query_cache_size=0
#query_cache_type=0

# Override bind-address
# In some systems bind-address defaults to 127.0.0.1, and with mysqldump SST
# it will have (most likely) disastrous consequences on donor node
bind-address=0.0.0.0

##
## WSREP options
##

# Full path to wsrep provider library or 'none'
wsrep_provider=/usr/lib/galera/libgalera_smm.so

# Provider specific configuration options
wsrep_provider_options=gcache.size=8192M

# Logical cluster name. Should be the same for all nodes.
wsrep_cluster_name="my_wsrep_cluster"

# Group communication system handle
wsrep_cluster_address=gcomm://$__wsrep_nodes__

# Human-readable node name (non-unique). Hostname by default.
#wsrep_node_name=

# Base replication <address|hostname>[:port] of the node.
# The values supplied will be used as defaults for state transfer receiving,
# listening ports and so on. Default: address of the first network interface.
wsrep_node_address=$__wsrep_node_address__

# Address for incoming client connections. Autodetect by default.
#wsrep_node_incoming_address=

# How many threads will process writesets from other nodes
wsrep_slave_threads=70

# DBUG options for wsrep provider
#wsrep_dbug_option

# Generate fake primary keys for non-PK tables (required for multi-master
# and parallel applying operation)
wsrep_certify_nonPK=1

# Maximum number of rows in write set
wsrep_max_ws_rows=131072

# Maximum size of write set
wsrep_max_ws_size=1073741824

# to enable debug level logging, set this to 1
wsrep_debug=0

# convert locking sessions into transactions
wsrep_convert_LOCK_to_trx=0

# how many times to retry deadlocked autocommits
wsrep_retry_autocommit=1

# change auto_increment_increment and auto_increment_offset automatically
wsrep_auto_increment_control=1

# retry autoinc insert, which failed for duplicate key error
wsrep_drupal_282555_workaround=0

# enable "strictly synchronous" semantics for read operations
wsrep_causal_reads=0

# Command to call when node status or cluster membership changes.
# Will be passed all or some of the following options:
# --status  - new status of this node
# --uuid    - UUID of the cluster
# --primary - whether the component is primary or not ("yes"/"no")
# --members - comma-separated list of members
# --index   - index of this node in the list
#wsrep_notify_cmd=

##
## WSREP State Transfer options
##

# State Snapshot Transfer method
wsrep_sst_method=rsync

# Address which donor should send State Snapshot to.
# Should be the address of THIS node. DON'T SET IT TO DONOR ADDRESS!!!
# (SST method dependent. Defaults to the first IP of the first interface)
#wsrep_sst_receive_address=

# SST authentication string. This will be used to send SST to joining nodes.
# Depends on SST method. For mysqldump method it is root:<root password>
wsrep_sst_auth=root:$__mysql_token__

# Desired SST donor name.
#wsrep_sst_donor=

# Reject client queries when donating SST (false)
#wsrep_sst_donor_rejects_queries=0

# Protocol version to use
# wsrep_protocol_version=
""")
