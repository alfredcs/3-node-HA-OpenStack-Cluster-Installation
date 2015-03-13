#!/usr/bin/env bash

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


CONF_DIR=/etc/contrail
set -x

if [ -f /etc/redhat-release ]; then
   is_redhat=1
   is_ubuntu=0
   web_svc=httpd
   mysql_svc=mysqld
   glance_ver=`rpm -q --qf  "%{VERSION}\n" openstack-glance`
fi

if [ -f /etc/lsb-release ] && egrep -q 'DISTRIB_ID.*Ubuntu' /etc/lsb-release; then
   is_ubuntu=1
   is_redhat=0
   web_svc=apache2
   mysql_svc=mysql
fi

function error_exit
{
    echo "${PROGNAME}: ${1:-''} ${2:-'Unknown Error'}" 1>&2
    exit ${3:-1}
}

chkconfig $mysql_svc 2>/dev/null
ret=$?
if [ $ret -ne 0 ]; then
    echo "MySQL is not enabled, enabling ..."
    chkconfig $mysql_svc on 2>/dev/null
fi

mysql_status=`service $mysql_svc status 2>/dev/null`
if [[ $mysql_status != *running* ]]; then
    echo "MySQL is not active, starting ..."
    service $mysql_svc restart 2>/dev/null
fi


# Use MYSQL_ROOT_PW from the environment or generate a new password
if [ ! -f $CONF_DIR/mysql.token ]; then
    if [ -n "$MYSQL_ROOT_PW" ]; then
	MYSQL_TOKEN=$MYSQL_ROOT_PW
    else
	MYSQL_TOKEN=$(openssl rand -hex 10)
    fi
    echo $MYSQL_TOKEN > $CONF_DIR/mysql.token
    chmod 400 $CONF_DIR/mysql.token
    echo show databases |mysql -u root &> /dev/null
    if [ $? -eq 0 ] ; then
        mysqladmin password $MYSQL_TOKEN
    else
        error_exit ${LINENO} "MySQL root password unknown, reset and retry"
    fi
else
    MYSQL_TOKEN=$(cat $CONF_DIR/mysql.token)
fi

source /etc/contrail/ctrl-details

# Check if ADMIN/SERVICE Password has been set
ADMIN_TOKEN=${ADMIN_TOKEN:-contrail123}
SERVICE_TOKEN=${SERVICE_TOKEN:-$(cat $CONF_DIR/service.token)}
OPENSTACK_INDEX=${OPENSTACK_INDEX:-0}
INTERNAL_VIP=${INTERNAL_VIP:-none}

controller_ip=$CONTROLLER
if [ "$INTERNAL_VIP" != "none" ]; then
    controller_ip=$INTERNAL_VIP
fi

cat > $CONF_DIR/openstackrc <<EOF
export OS_USERNAME=admin
export OS_PASSWORD=$ADMIN_TOKEN
export OS_TENANT_NAME=admin
export OS_AUTH_URL=http://$controller_ip:5000/v2.0/
export OS_NO_CACHE=1
EOF

for cfg in api registry; do
    if [ $is_ubuntu -eq 1 ] ; then
        openstack-config --set /etc/glance/glance-$cfg.conf DEFAULT sql_connection sqlite:////var/lib/glance/glance.sqlite
    fi
    if [ "$INTERNAL_VIP" != "none" ]; then
        openstack-config --set /etc/glance/glance-$cfg.conf DEFAULT sql_connection mysql://glance:glance@$CONTROLLER:3306/glance
    fi
done

for APP in glance; do
    # Required only in first openstack node, as the mysql db is replicated using galera.
    if [ "$OPENSTACK_INDEX" -eq 1 ]; then
        openstack-db -y --init --service $APP --rootpw "$MYSQL_TOKEN"
        glance-manage db_sync
        if [ $is_ubuntu -eq 1 ] ; then
            chown glance /var/lib/glance/glance.sqlite
            chgrp glance /var/lib/glance/glance.sqlite
        fi
    fi
done

export ADMIN_TOKEN
export SERVICE_TOKEN

for cfg in api; do
    openstack-config --set /etc/glance/glance-$cfg.conf DEFAULT notifier_strategy noop
   if [ $is_ubuntu -eq 0 ] ; then
        if [ "$glance_ver" == "2014.1.1" ]; then
            #launchpad workaround:https://bugzilla.redhat.com/show_bug.cgi?id=1090648
            openstack-config --set /etc/glance/glance-$cfg.conf DEFAULT db_enforce_mysql_charset False
        fi
    fi
done

for cfg in api registry; do
    openstack-config --set /etc/glance/glance-$cfg.conf DEFAULT sql_idle_timeout 3600
    openstack-config --set /etc/glance/glance-$cfg.conf keystone_authtoken admin_tenant_name service
    openstack-config --set /etc/glance/glance-$cfg.conf keystone_authtoken admin_user glance
    openstack-config --set /etc/glance/glance-$cfg.conf keystone_authtoken admin_password $SERVICE_TOKEN
    openstack-config --set /etc/glance/glance-$cfg.conf paste_deploy flavor keystone
    if [ "$INTERNAL_VIP" != "none" ]; then
        openstack-config --set /etc/glance/glance-$cfg.conf keystone_authtoken auth_host $INTERNAL_VIP
        openstack-config --set /etc/glance/glance-$cfg.conf keystone_authtoken auth_port 5000
        openstack-config --set /etc/glance/glance-$cfg.conf database idle_timeout 180
        openstack-config --set /etc/glance/glance-$cfg.conf database min_pool_size 100
        openstack-config --set /etc/glance/glance-$cfg.conf database max_pool_size 700
        openstack-config --set /etc/glance/glance-$cfg.conf database max_overflow 100
        openstack-config --set /etc/glance/glance-$cfg.conf database retry_interval 5
        openstack-config --set /etc/glance/glance-$cfg.conf database max_retries -1
        openstack-config --set /etc/glance/glance-$cfg.conf database db_max_retries 3
        openstack-config --set /etc/glance/glance-$cfg.conf database db_retry_interval 1
        openstack-config --set /etc/glance/glance-$cfg.conf database connection_debug 10
        openstack-config --set /etc/glance/glance-$cfg.conf database pool_timeout 120
    fi
done
if [ "$INTERNAL_VIP" != "none" ]; then
    # Openstack HA specific config
    openstack-config --set /etc/glance/glance-api.conf DEFAULT bind_port 9393
    openstack-config --set /etc/glance/glance-api.conf DEFAULT rabbit_host $AMQP_SERVER
    openstack-config --set /etc/glance/glance-api.conf DEFAULT rabbit_port 5673
    openstack-config --set /etc/glance/glance-api.conf DEFAULT swift_store_auth_address $INTERNAL_VIP:5000/v2.0/
fi

if [ "$OPENSTACK_INDEX" -eq 1 ]; then
    glance-manage db_sync
fi

echo "======= Enabling the services ======"

for svc in $web_svc memcached; do
    chkconfig $svc on
done

for svc in supervisor-openstack; do
    chkconfig $svc on
done

echo "======= Starting the services ======"

for svc in $web_svc memcached; do
    service $svc restart
done

# Listen at supervisor-openstack port
status=$(service supervisor-openstack status | grep -s -i running >/dev/null 2>&1  && echo "running" || echo "stopped")
if [ $status == 'stopped' ]; then
    service supervisor-openstack start
    sleep 5
    supervisorctl -s http://localhost:9010 stop all
fi

# Start glance services
for svc in glance-api glance-registry; do
    service $svc restart
done
