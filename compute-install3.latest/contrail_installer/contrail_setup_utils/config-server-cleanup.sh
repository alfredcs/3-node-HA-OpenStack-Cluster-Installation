#!/usr/bin/env bash

#
# Remove OpenStack configuration from a server.
#

pycassaShell -f drop-cassandra-cfgm-keyspaces

# shutdown all the services
for svc in supervisor-config quantum-server puppet-server; do
    chkconfig $svc off > /dev/null 2>&1
    service $svc stop > /dev/null 2>&1
done

for svc in api objectstore scheduler cert consoleauth novncproxy conductor; do
    svc=openstack-nova-$svc
    chkconfig $svc off > /dev/null 2>&1
    service $svc stop > /dev/null 2>&1
done

for svc in api registry; do
    svc=openstack-glance-$svc
    chkconfig $svc off > /dev/null 2>&1
    service $svc stop > /dev/null 2>&1
done

for svc in api scheduler; do
    svc=openstack-cinder-$svc
    chkconfig $svc off > /dev/null 2>&1
    service $svc stop > /dev/null 2>&1
done

CONF_DIR=/etc/contrail

if [ -n "$MYSQL_ROOT_PW" ]; then
    MYSQL_TOKEN=$MYSQL_ROOT_PW
elif [ -f $CONF_DIR/mysql.token ]; then
    MYSQL_TOKEN=$(cat $CONF_DIR/mysql.token)
fi

if [ -z "$MYSQL_TOKEN" ]; then
    echo "Please provide MySQL root password"
    exit 1
fi

for svc in keystone nova glance cinder; do
    openstack-db -y --drop --service $svc --rootpw "$MYSQL_TOKEN"
done

rm -rf /etc/keystone/ssl
rm -f /etc/contrail/service.token
rm -f /etc/contrail/keystonerc
rm -f /etc/contrail/openstackrc

if [ -n "$DISABLE_MYSQL" ]; then
    mysqladmin --password="$MYSQL_TOKEN" password ""
    rm -f /etc/contrail/mysql.token
    chkconfig mysqld off > /dev/null 2>&1
    service mysqld stop > /dev/null 2>&1
fi

# TODO: determine what needs to be removed
for subdir in keys buckets images; do
    ls /var/lib/nova/$subdir
done

for file in $(ls /var/lib/glance/images); do
    rm -f $file
done

# Remove keystone keys
for svc in nova glance quantum; do
    rm -f /var/lib/$svc/keystone-signing/*.pem
done

rm -f /var/lib/cinder/*.pem
