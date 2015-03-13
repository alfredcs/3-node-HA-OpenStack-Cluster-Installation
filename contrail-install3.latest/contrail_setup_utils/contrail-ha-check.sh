#!/bin/bash

# Purpose of the script is to check the state of galera cluster
# Author - Sanju Abraham

while true; do
    sleep 5
    /opt/contrail/bin/contrail-cmon-monitor.sh
done
