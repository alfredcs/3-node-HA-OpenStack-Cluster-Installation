#!/usr/bin/env bash

CONFIG_FILE="/etc/contrail/dns.conf"
OLD_CONFIG_FILE=/etc/contrail/dns_param
SIGNATURE="DNS configuration options, generated from $OLD_CONFIG_FILE"

# Remove old style command line arguments from .ini file.
perl -ni -e 's/command=.*/command=\/usr\/bin\/dnsd/g; print $_;' /etc/contrail/supervisord_control_files/contrail-dns.ini

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

(
cat << EOF
#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#
# $SIGNATURE
#

[DEFAULT]
# collectors= # Provided by discovery server
# dns_config_file=dns_config.xml
  hostip=$HOSTIP # Resolved IP of `hostname`
  hostname=$HOSTNAME # Retrieved as `hostname`
# http_server_port=8092
# dns_server_port=53
# log_category=
# log_disable=0
  log_file=/var/log/contrail/dns.log
# log_files_count=10
# log_file_size=1048576 # 1MB
# log_level=SYS_NOTICE
# log_local=0
# test_mode=0

[DISCOVERY]
# port=5998
  server=$DISCOVERY # discovery-server IP address

[IFMAP]
  certs_store=$CERT_OPTS
  password=$IFMAP_PASWD
# server_url= # Provided by discovery server, e.g. https://127.0.0.1:8443
  user=$IFMAP_USER


EOF
) > $CONFIG_FILE
