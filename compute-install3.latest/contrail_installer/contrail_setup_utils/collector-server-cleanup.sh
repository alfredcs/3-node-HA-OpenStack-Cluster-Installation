#!/usr/bin/env bash

#cleanup script for analytics package under supervisord

for svc in contrail-collector contrail-analytics-api ; do
    supervisorctl -s http://localhost:9002 stop $svc
done
chkconfig supervisor-analytics off
service supervisor-analytics stop
