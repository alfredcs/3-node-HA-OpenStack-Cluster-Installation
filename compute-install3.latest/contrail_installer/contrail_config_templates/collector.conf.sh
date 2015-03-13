#!/usr/bin/env bash

CONFIG_FILE="/etc/contrail/contrail-collector.conf"
OLD_CONFIG_FILE=/etc/contrail/vizd_param
SIGNATURE="Collector configuration options, generated from $OLD_CONFIG_FILE"

# Remove old style command line arguments from .ini file.
perl -ni -e 's/command=.*/command=\/usr\/bin\/vizd/g; print $_;' /etc/contrail/supervisord_analytics_files/contrail-collector.ini

if [ ! -e $OLD_CONFIG_FILE ]; then
    exit
fi

# Ignore if the converted file is already generated once before
if [ -e $CONFIG_FILE ]; then
    grep --quiet "$SIGNATURE" $CONFIG_FILE > /dev/null

    # Exit if configuraiton already converted!
    if [ $? == 0 ]; then
        exit
    fi
fi

source $OLD_CONFIG_FILE 2>/dev/null || true

if [ -z $ANALYTICS_DATA_TTL ]; then
    ANALYTICS_DATA_TTL=48
fi

if [ -z $ANALYTICS_SYSLOG_PORT ]; then
    ANALYTICS_SYSLOG_PORT=0
fi

if [ -z $CASSANDRA_SERVER_LIST ]; then
    # Try to retrieve ' ' separated list of tokens,
    CASSANDRA_SERVER_LIST=`\grep CASSANDRA_SERVER_LIST $OLD_CONFIG_FILE | awk -F '=' '{print $2}'` || true
fi

(
cat << EOF
#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#
# $SIGNATURE
#

[DEFAULT]
  analytics_data_ttl=$ANALYTICS_DATA_TTL
  cassandra_server_list=$CASSANDRA_SERVER_LIST
# dup=0
  hostip=$HOST_IP # Resolved IP of `hostname`
# hostname= # Retrieved as `hostname`
  http_server_port=$HTTP_SERVER_PORT
# log_category=
# log_disable=0
  log_file=$LOG_FILE
# log_files_count=10
# log_file_size=1048576 # 1MB
# log_level=SYS_NOTICE
# log_local=0
  syslog_port=$ANALYTICS_SYSLOG_PORT
# test_mode=0

[COLLECTOR]
  port=$LISTEN_PORT
# server=0.0.0.0

[DISCOVERY]
# port=5998
  server=$DISCOVERY # discovery_server IP address

[REDIS]
  port=6379
  server=127.0.0.1

EOF
) > $CONFIG_FILE
