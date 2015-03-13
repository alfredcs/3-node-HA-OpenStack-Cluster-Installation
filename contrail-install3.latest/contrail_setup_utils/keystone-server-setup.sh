#!/usr/bin/env bash

CONF_DIR=/etc/contrail
set -x

if [ -f /etc/redhat-release ]; then
   is_redhat=1
   is_ubuntu=0
   web_svc=httpd
   mysql_svc=mysqld
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

# Exclude port 35357 from the available ephemeral port range
sysctl -w net.ipv4.ip_local_reserved_ports=35357,35358,$(cat /proc/sys/net/ipv4/ip_local_reserved_ports)
# Make the exclusion of port 35357 persistent
grep '^net.ipv4.ip_local_reserved_ports' /etc/sysctl.conf > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "net.ipv4.ip_local_reserved_ports = 35357,35358" >> /etc/sysctl.conf
else
    sed -i 's/net.ipv4.ip_local_reserved_ports\s*=\s*/net.ipv4.ip_local_reserved_ports=35357,35358,/' /etc/sysctl.conf
fi

chkconfig $mysql_svc 2>/dev/null
ret=$?
if [ $ret -ne 0 ]; then
    echo "MySQL is not enabled, enabling ..."
    chkconfig mysqld on 2>/dev/null
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

KEYSTONE_CONF=${KEYSTONE_CONF:-/etc/keystone/keystone.conf}

source /etc/contrail/ctrl-details

# Check if ADMIN/SERVICE Password has been set
ADMIN_PASSWORD=${ADMIN_TOKEN:-contrail123}
SERVICE_PASSWORD=${SERVICE_TOKEN:-$(/opt/contrail/contrail_installer/contrail_setup_utils/setup-service-token.sh; cat $CONF_DIR/service.token)}

openstack-config --set /etc/keystone/keystone.conf DEFAULT admin_token $SERVICE_PASSWORD

# Stop keystone if it is already running (to reload the new admin token)
service supervisor-openstack status >/dev/null 2>&1 &&
service supervisor-openstack stop

# Listen at supervisor-openstack port
status=$(service supervisor-openstack status | grep -s -i running >/dev/null 2>&1  && echo "running" || echo "stopped")
if [ $status == 'stopped' ]; then
    service supervisor-openstack start
    sleep 5
    supervisorctl -s http://localhost:9010 stop all
fi

# Start and enable the Keystone service
service keystone restart
chkconfig supervisor-openstack on

if [ ! -d /etc/keystone/ssl ]; then
    keystone-manage pki_setup --keystone-user keystone --keystone-group keystone
    chown -R keystone.keystone /etc/keystone/ssl
fi

if [ -d /var/log/keystone ]; then
    chown -R keystone:keystone /var/log/keystone
fi

# Set up a keystonerc file with admin password
OPENSTACK_INDEX=${OPENSTACK_INDEX:-0}
INTERNAL_VIP=${INTERNAL_VIP:-none}
if [ "$INTERNAL_VIP" != "none" ]; then
    export SERVICE_ENDPOINT=${SERVICE_ENDPOINT:-$AUTH_PROTOCOL://$CONTROLLER:${CONFIG_ADMIN_PORT:-35358}/v2.0}
else
    export SERVICE_ENDPOINT=${SERVICE_ENDPOINT:-$AUTH_PROTOCOL://$CONTROLLER:${CONFIG_ADMIN_PORT:-35357}/v2.0}
fi

controller_ip=$CONTROLLER
if [ "$INTERNAL_VIP" != "none" ]; then
    controller_ip=$INTERNAL_VIP
fi

cat > $CONF_DIR/openstackrc <<EOF
export OS_USERNAME=admin
export OS_PASSWORD=$ADMIN_PASSWORD
export OS_TENANT_NAME=admin
export OS_AUTH_URL=${AUTH_PROTOCOL}://$controller_ip:5000/v2.0/
export OS_NO_CACHE=1
EOF

cat > $CONF_DIR/keystonerc <<EOF
export OS_USERNAME=admin
export SERVICE_TOKEN=$SERVICE_PASSWORD
export OS_SERVICE_ENDPOINT=$SERVICE_ENDPOINT
EOF

export ADMIN_PASSWORD
export SERVICE_PASSWORD

if [ "$INTERNAL_VIP" != "none" ]; then
    # Openstack HA specific config
    openstack-config --set /etc/keystone/keystone.conf sql connection mysql://keystone:keystone@$CONTROLLER:3306/keystone
else
    openstack-config --set /etc/keystone/keystone.conf sql connection mysql://keystone:keystone@127.0.0.1/keystone
fi
for APP in keystone; do
    # Required only in first openstack node, as the mysql db is replicated using galera.
    if [ "$OPENSTACK_INDEX" -eq 1 ]; then
        openstack-db -y --init --service $APP --rootpw "$MYSQL_TOKEN"
    fi
done

if [ "$INTERNAL_VIP" != "none" ]; then
    # Required only in first openstack node, as the mysql db is replicated using galera.
    if [ "$OPENSTACK_INDEX" -eq 1 ]; then
        (source $CONF_DIR/keystonerc; bash contrail-ha-keystone-setup.sh $INTERNAL_VIP)
        if [ $? != 0 ]; then
            exit 1
        fi
    fi
else
    (source $CONF_DIR/keystonerc; bash contrail-keystone-setup.sh $CONTROLLER)
    if [ $? != 0 ]; then
        exit 1
    fi
fi

# wait for the keystone service to start
tries=0
while [ $tries -lt 10 ]; do
    $(source $CONF_DIR/keystonerc; keystone user-list >/dev/null 2>&1)
    if [ $? -eq 0 ]; then break; fi;
    tries=$(($tries + 1))
    sleep 1
done

# Check if ADMIN/SERVICE Password has been set

# Update all config files with service username and password
for svc in keystone; do
    openstack-config --del /etc/$svc/$svc.conf database connection
    openstack-config --set /etc/$svc/$svc.conf keystone_authtoken admin_tenant_name service
    openstack-config --set /etc/$svc/$svc.conf keystone_authtoken admin_user $svc
    openstack-config --set /etc/$svc/$svc.conf keystone_authtoken admin_password $SERVICE_PASSWORD
    openstack-config --set /etc/$svc/$svc.conf DEFAULT log_file /var/log/keystone/keystone.log
    openstack-config --set /etc/$svc/$svc.conf sql connection mysql://keystone:keystone@127.0.0.1/keystone
    openstack-config --set /etc/$svc/$svc.conf catalog template_file /etc/keystone/default_catalog.templates
    openstack-config --set /etc/$svc/$svc.conf catalog driver keystone.catalog.backends.sql.Catalog
    openstack-config --set /etc/$svc/$svc.conf identity driver keystone.identity.backends.sql.Identity
    openstack-config --set /etc/$svc/$svc.conf token driver keystone.token.backends.memcache.Token
    openstack-config --set /etc/$svc/$svc.conf ec2 driver keystone.contrib.ec2.backends.sql.Ec2
    openstack-config --set /etc/$svc/$svc.conf DEFAULT onready keystone.common.systemd
    openstack-config --set /etc/$svc/$svc.conf memcache servers 127.0.0.1:11211
done

# Required only in first openstack node, as the mysql db is replicated using galera.
if [ "$OPENSTACK_INDEX" -eq 1 ]; then
    keystone-manage db_sync
fi

if [ "$INTERNAL_VIP" != "none" ]; then
    # Openstack HA specific config
    openstack-config --set /etc/keystone/keystone.conf sql connection mysql://keystone:keystone@$CONTROLLER:3306/keystone
    openstack-config --set /etc/keystone/keystone.conf token driver keystone.token.backends.sql.Token
    openstack-config --del /etc/keystone/keystone.conf memcache servers
    openstack-config --set /etc/keystone/keystone.conf database idle_timeout 180
    openstack-config --set /etc/keystone/keystone.conf database min_pool_size 100
    openstack-config --set /etc/keystone/keystone.conf database max_pool_size 700
    openstack-config --set /etc/keystone/keystone.conf database max_overflow 100
    openstack-config --set /etc/keystone/keystone.conf database retry_interval 5
    openstack-config --set /etc/keystone/keystone.conf database max_retries -1
    openstack-config --set /etc/keystone/keystone.conf database db_max_retries -1
    openstack-config --set /etc/keystone/keystone.conf database db_retry_interval 1
    openstack-config --set /etc/keystone/keystone.conf database connection_debug 10
    openstack-config --set /etc/keystone/keystone.conf database pool_timeout 120
fi

# Increase memcached 'item_size_max' to 10MB, default is 1MB
# Work around for bug https://bugs.launchpad.net/keystone/+bug/1242620
item_size_max="10m"
if [ $is_ubuntu -eq 1 ] ; then
    memcache_conf='/etc/memcached.conf'
    opts=$(grep "\-I " ${memcache_conf})
    if [ $? -ne 0 ]; then
        echo "-I ${item_size_max}" >> ${memcache_conf}
    fi
elif [ $is_redhat -eq 1 ]; then
    memcache_conf='/etc/sysconfig/memcached'
    opts=$(grep OPTIONS ${memcache_conf} | grep -Po '".*?"')
    if [ $? -ne 0 ]; then
        #Write option to memcached config file
        echo "OPTIONS=\"-I ${item_size_max}\"" >> ${memcache_conf}
    else
        #strip the leading and trailing qoutes
        opts=$(echo "$opts" | sed -e 's/^"//'  -e 's/"$//')
        grep OPTIONS ${memcache_conf} | grep -Po '".*?"' | grep "\-I"
        if [ $? -ne 0 ]; then
            #concatenate with the existing options.
            opts="$opts -I ${item_size_max}"
            sed -i "s/OPTIONS.*/OPTIONS=\"${opts}\"/g" ${memcache_conf}
        fi
    fi
fi

# Create link /usr/bin/nodejs to /usr/bin/node
if [ ! -f /usr/bin/nodejs ]; then 
    ln -s /usr/bin/node /usr/bin/nodejs
fi

echo "======= Enabling the keystone services ======"

for svc in $web_svc memcached; do
    chkconfig $svc on
done

echo "======= Starting the services ======"

for svc in $web_svc memcached; do
    service $svc restart
done

# Start keysotne service
service keystone restart

