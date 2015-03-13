#!/usr/bin/env bash

CONFIG_FILE="/etc/contrail/contrail-control.conf"
OLD_CONFIG_FILE=/etc/contrail/control_param
SIGNATURE="Control-node configuration options, generated from $OLD_CONFIG_FILE"

# Remove old style command line arguments from .ini file.
perl -ni -e 's/command=.*/command=\/usr\/bin\/contrail-control/g; print $_;' /etc/contrail/supervisord_control_files/contrail-control.ini

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
# bgp_config_file=bgp_config.xml
# bgp_port=179
# collectors= # Provided by discovery server
  hostip=$HOSTIP # Resolved IP of `hostname`
  hostname=$HOSTNAME # Retrieved as `hostname`
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
  server=$DISCOVERY # discovery-server IP address

[IFMAP]
  certs_store=$CERT_OPTS
  password=$IFMAP_PASWD
# server_url= # Provided by discovery server, e.g. https://127.0.0.1:8443
  user=$IFMAP_USER


EOF
) > $CONFIG_FILE
