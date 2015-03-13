import string

template = string.Template("""
[MYSQLD]
user=mysql
basedir=/usr/
datadir=/var/lib/mysql
socket=/var/lib/mysql/mysql.sock
pid-file=mysqld.pid
port=3306
log-error=error.log
#log-output=FILE
#relay-log=relay-bin
### INNODB OPTIONS 
innodb-buffer-pool-size=500M
innodb-additional-mem-pool-size=1000M
innodb-flush-log-at-trx-commit=2
innodb-file-per-table=1
innodb-data-file-path = ibdata1:100M:autoextend
## You may want to tune the below depending on number of cores and disk sub
innodb-read-io-threads=4
innodb-write-io-threads=4
innodb-doublewrite=1
innodb-log-file-size=256M
innodb-log-buffer-size=32M
#innodb-buffer-pool-instances=4
innodb-log-files-in-group=2
innodb-thread-concurrency=0
#innodb-file-format=barracuda
innodb-flush-method = O_DIRECT
innodb-locks-unsafe-for-binlog=1
innodb-autoinc-lock-mode=2
## avoid statistics update when doing e.g show tables
innodb-stats-on-metadata=0
engine-condition-pushdown=1
default-storage-engine=innodb

# CHARACTER SET
#collation-server = utf8_unicode_ci
#init-connect='SET NAMES utf8'
#character-set-server = utf8

# REPLICATION SPECIFIC - GENERAL
#server-id must be unique across all mysql servers participating in replication.
#server-id=SERVERID
#auto_increment_increment=2
#auto_increment_offset=SERVERID
# REPLICATION SPECIFIC
binlog_format=ROW
#log-bin=binlog
#relay-log=relay-bin
#expire_logs_days=7
#log-slave-updates=1
#log-bin=binlog
# OTHER THINGS, BUFFERS ETC
key_buffer_size = 24M
tmp_table_size = 64M
max_heap_table_size = 64M
max-allowed-packet = 512M
#sort-buffer-size = 256K
#read-buffer-size = 256K
#read-rnd-buffer-size = 512K
#myisam-sort-buffer_size = 8M
skip-name-resolve
memlock=0
sysdate-is-now=1
max-connections=10000
thread-cache-size=512
query-cache-type = 0
query-cache-size = 16M
table-open_cache=1024
lower-case-table-names=0
##
## WSREP options
##

# Full path to wsrep provider library or 'none'
wsrep_provider=/usr/lib64/galera/libgalera_smm.so

wsrep_node_address=$__wsrep_node_address__
# Provider specific configuration options
wsrep_provider_options="gcache.size=8192M"

# Logical cluster name. Should be the same for all nodes.
wsrep_cluster_name="my_wsrep_cluster"

# Group communication system handle
wsrep_cluster_address=gcomm://$__wsrep_nodes__

# Human-readable node name (non-unique). Hostname by default.
#wsrep_node_name=

# Address for incoming client connections. Autodetect by default.
#wsrep_node_incoming_address=

# How many threads will process writesets from other nodes
wsrep_slave_threads=8

# DBUG options for wsrep provider
#wsrep_dbug_option

# Generate fake primary keys for non-PK tables (required for multi-master
# and parallel applying operation)
wsrep_certify_nonPK=1

# Location of the directory with data files. Needed for non-mysqldump
# state snapshot transfers. Defaults to mysql_real_data_home.
#wsrep_data_home_dir=

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

# replicate myisam
wsrep_replicate_myisam=1
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
# ClusterControl currently DOES NOT support wsrep_sst_method=mysqldump
wsrep_sst_method=xtrabackup

# Address on THIS node to receive SST at. DON'T SET IT TO DONOR ADDRESS!!!
# (SST method dependent. Defaults to the first IP of the first interface)
#wsrep_sst_receive_address=

# SST authentication string. This will be used to send SST to joining nodes.
# Depends on SST method. For mysqldump method it is root:<root password>
wsrep_sst_auth=root:$__mysql_token__

# Desired SST donor name.
#wsrep_sst_donor=

# Protocol version to use
# wsrep_protocol_version=
[MYSQL]
socket=/var/lib/mysql/mysql.sock
#default-character-set=utf8
[client]
socket=/var/lib/mysql/mysql.sock
#default-character-set=utf8
[mysqldump]
max-allowed-packet = 512M
#default-character-set=utf8
[MYSQLD_SAFE]
pid-file=mysqld.pid
log-error=error.log
basedir=/usr/
datadir=/var/lib/mysql
""")
