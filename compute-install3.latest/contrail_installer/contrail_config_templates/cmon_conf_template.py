import string

template = string.Template("""
#cmon config file
# id and name of cluster that this cmon agent is monitoring. 
# Must be unique for each monitored cluster, like server-id in mysql
cluster_id=1
name=contrail-cluster_$__mysql_node_address__

# os = [redhat|debian]
os=debian

# skip_name_resolve = [0|1] - set 1 if you use ip addresses only everywhere
skip_name_resolve=1

# mode = [controller|agent|dual]
mode=controller

# type = [mysqlcluster|replication|galera]
type=galera

# location of mysql install, e.g /usr/ or /usr/local/mysql
mysql_basedir=/usr

## CMON DB config  - mysql_password is for the 'cmon' user
mysql_port=33306
mysql_hostname=$__mysql_node_address__
mysql_password=cmon


#hostname is the hostname of the current host
hostname=$__mysql_node_address__

# ndb_connectstring  - comma-separated list of management servers: a:1186,b:1196
#ndb_connectstring=127.0.0.1

## The user that can SSH without password to the oter nodes
osuser=root

# location of cmon.pid file. The pidfile is written in /tmp/ by default
pidfile=/var/run/

# logfile is default to syslog.
logfile=/var/log/cmon.log

# collection intervals (in seconds)
db_stats_collection_interval=30
host_stats_collection_interval=30

# mysql servers in the cluster. "," or " " sep. list
mysql_server_addresses=$__mysql_nodes__

# mgm and data nodes are only used to MySQL Cluster "," or " " sep. list
datanode_addresses=
mgmnode_addresses=


wwwroot=/var/www/

# configuration file directory for database servers (location of config.ini, my.cnf etc)
# on RH, usually it is /etc/, on Debian/Ubuntu /etc/mysql. If different please set:
#db_configdir=
ssh_identity=''
ssh_opts=-q
ssh_port=22

nodaemon=1
monitored_mountpoints=/var/lib/mysql
mysql_bindir=/usr/bin/
""")
