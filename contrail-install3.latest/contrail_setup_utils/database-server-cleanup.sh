#!/usr/bin/env bash

#cleanup script for database package under supervisord
# shutdown all the services
for svc in zookeeper supervisord-contrail-database; do
    chkconfig $svc off > /dev/null 2>&1
    service $svc stop > /dev/null 2>&1
done

