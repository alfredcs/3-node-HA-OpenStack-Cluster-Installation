#!/usr/bin/env bash

for svc in openstack-nova-compute supervisor-vrouter; do
    chkconfig $svc off
done

for svc in openstack-nova-compute supervisor-vrouter; do
    service $svc stop
done
