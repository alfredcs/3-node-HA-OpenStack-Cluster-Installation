#!/bin/bash
set -x
function usage() {
cat <<EOF
usage: $0 options

This script will install Glance on this Openstack Controller

Example:
        glance_install.sh [-L] -v openstack_controller_vip -F first_openstack_controller -S second_openstack_controller -T third_openstack_controller [-g glance_keyston_passwd] [-G glance_database_passwd]  [-R mysql_root_password] 

OPTIONS:
  -h -- Help Show this message
  -F -- The first contrail controller's IP address
  -g -- Glance Keystone password
  -G -- Glance database password
  -L -- Use SSL
  -S -- The second contrail controller's IP address
  -T -- The third contrail controller's IP address
  -V -- Verbose Verbose output
  -v -- VIP of the openstack controller

EOF
}
first_openstack_controller=""
KEYSTONE_CMD=keystone
HTTP_CMD=http
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
[[ $# -lt 1 ]] && { usage; exit 1; }
while getopts "hF:g:G:LR:S:T:v:VD" OPTION; do
case "$OPTION" in
h)
        usage
        exit 0
        ;;
F)
        first_openstack_controller="$OPTARG"
        ;;
g)
	GLANCE_KSPASS="$OPTARG"
	;;
G)
	GLANCE_DBPASS="$OPTARG"
	;;
L)
	KEYSTONE_CMD="keystone --insecure"
	HTTP_CMD=https
	;;
R)
	MYSQL_ROOT_PASS="$OPTARG"
	;;
S)
        second_openstack_controller="$OPTARG"
        ;;
T)
        third_openstack_controller="$OPTARG"
        ;;
v)
        openstack_controller_vip="$OPTARG"
        ;;
V)
        display_version
        exit 0
        ;;
D)
        DEBUG=1
        ;;
\?)
        echo "Invalid option: -"$OPTARG"" >&2
        usage
        exit 1
        ;;
:)
        usage
        exit 1
        ;;
esac
done

local_controller=`egrep $HOSTNAME /etc/hosts|grep -v ^#|head -1| awk '{print $1}'`
if [[  ${first_openstack_controller} == ${local_controller}  ]]; then
	echo "Installing Glance on the firsth Openstack controller node ......"
else
	###
	# Get Keys
	###
	#[[ -f .keystone_grants ]] && { rm -rf .keystone_grants; rm -rf eystone_grants.enc; }
	#curl --insecure -o keystone_grants.enc https://${first_openstack_controller}/.tmp/keystone_grants.enc
	#[[  -f keystone/newkey.pem && -f keystone_grants.enc ]] && openssl rsautl -decrypt -inkey keystone/newkey.pem -in keystone_grants.enc -out .keystone_grants
	[[ ! -f  ./.keystone_grants ]] && { echo "Require credential file from Openstacl installation!"; exit 1; }
fi
GLANCE_KSPASS=${GLANCE_KSPASS:-`cat ./.keystone_grants|grep -i GLANCE_KSPASS| grep -v ^#|cut -d= -f2`}
GLANCE_DBPASS=${GLANCE_DBPASS:-`cat ./.keystone_grants|grep -i GLANCE_DBPASS| grep -v ^#|cut -d= -f2`}
MYSQL_ROOT_PASS=${MYSQL_ROOT_PASS:-`cat ./.keystone_grants|grep -i MYSQL_ROOT_PASS| grep -v ^#|cut -d= -f2`}
openstack_controller_vip=${openstack_controller_vip:-"cat ./.keystone_grants|grep -i openstack_controller| grep -v ^#|cut -d= -f2"}
domain_name=`echo $HOSTNAME|cut -d\. -f2,3,4,5`
domain_name=${domain_name:-"default.domain"}
[ `rpm -qa| grep openstack-glance|wc -l` -gt 0 ] && rpm -e --nodeps `rpm -qa|egrep 'openstack-glance|qpid-cpp-server'`
[ `rpm -qa| grep rabbitmq-server|wc -l` -gt 0 ] && rpm -e --nodeps `rpm -qa|egrep 'rabbitmq-server|erlang'`
[ `rpm -qa| grep openstack-glance|wc -l` -lt 1 ] && yum -y install  --disablerepo=* --enablerepo=havana_install_repo110 openstack-glance qpid-cpp-server memcached rabbitmq-server
[[ -f ~/contrc ]] && source ~/contrc
service openstack-glance-api stop
service openstack-glance-registry stop
openstack-config --set /etc/glance/glance-api.conf \
        DEFAULT sql_connection mysql://glance:$GLANCE_DBPASS@${local_controller}/glance
openstack-config --set /etc/glance/glance-api.conf \
	DEFAULT notifier_strategy noop
openstack-config --set /etc/glance/glance-registry.conf \
        DEFAULT sql_connection mysql://glance:$GLANCE_DBPASS@${local_controller}/glance
if [ `${KEYSTONE_CMD} user-list| grep glance | wc -l` -lt 1 ]; then
        ${KEYSTONE_CMD} user-create --name=glance --pass=$GLANCE_KSPASS --email=glance@$domain_name
        ${KEYSTONE_CMD} user-role-add --user=glance --tenant=service --role=admin
fi
if [ -f /etc/glance/glance-api.conf -o  /etc/glance/glance-registry.conf ]; then
        sed -i "/^auth_host/d" /etc/glance/glance-api.conf
#        sed -i "/notifier_strategy/ s/notifier_strategy/#notifier_strategy/" /etc/glance/glance-api.conf
        sed -i "/^auth_host/d" /etc/glance/glance-registry.conf
        sed -i "/^admin_user/d" /etc/glance/glance-api.conf
        sed -i "/^admin_user/d" /etc/glance/glance-registry.conf
        sed -i "/^admin_tenant_name/d" /etc/glance/glance-api.conf
        sed -i "/^admin_tenant_name/d" /etc/glance/glance-registry.conf
        sed -i "/^admin_password/d" /etc/glance/glance-api.conf
        sed -i "/^qpid_/d" /etc/glance/glance-api.conf
        sed -i "/^admin_password/d" /etc/glance/glance-registry.conf
        #sed -i "/^sql_connection/d" /etc/glance/glance-api.conf
        #sed -i "/^sql_connection/d" /etc/glance/glance-registry.conf
fi
if [[ ${first_openstack_controller} == ${local_controller}  ]]; then
	#/usr/bin/openstack-db --drop --yes --rootpw ${MYSQL_ROOT_PASS}  --service glance
	[[ ! -z `mysql -uroot -p${MYSQL_ROOT_PASS} -qfsBe "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='glance'"` ]] &&  mysql -uroot -p${MYSQL_ROOT_PASS} -qfsBe "drop database glance"
	#openstack-db --init --service glance --password $GLANCE_DBPASS
	echo "create database glance;" > /tmp/._glance.sql
	echo "grant all on glance.* to glance@'%' identified by '$GLANCE_DBPASS';" >> /tmp/._glance.sql
	echo "grant all on glance.* to glance@'localhost' identified by '$GLANCE_DBPASS';" >> /tmp/._glance.sql
	echo "grant all on glance.* to glance@'$HOSTNAME' identified by '$GLANCE_DBPASS';" >> /tmp/._glance.sql
	mysql -uroot -p${MYSQL_ROOT_PASS} < /tmp/._glance.sql
	glance-manage db_sync
	[[ $? -ne 0 ]] && { echo "Glance DB init failed"; exit 1; }
	#[ -f ~/glance/glance.sql ] && mysql -u root -p < ~/glance/glance.sql
fi
openstack-config --set /etc/glance/glance-api.conf keystone_authtoken auth_host ${openstack_controller_vip}
openstack-config --set /etc/glance/glance-api.conf DEFAULT rabbit_host ${openstack_controller_vip}
#openstack-config --set /etc/glance/glance-api.conf DEFAULT notifier_strategy rabbit
sed -i "/notifier_strategy/ s/^#notifier_strategy=rabbit/notifier_strategy=rabbit/" /etc/glance/glance-api.conf
sed -i "/notifier_strategy/ s/^#notifier_strategy=qpid/notifier_strategy=rabbit/" /etc/glance/glance-api.conf
openstack-config --set /etc/glance/glance-api.conf keystone_authtoken admin_user glance
openstack-config --set /etc/glance/glance-api.conf keystone_authtoken admin_tenant_name service
openstack-config --set /etc/glance/glance-api.conf keystone_authtoken admin_password $GLANCE_KSPASS
if [[ ${HTTP_CMD} == "https" ]]; then
	openstack-config --set /etc/glance/glance-api.conf keystone_authtoken insecure True
	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_host ${openstack_controller_vip}
	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_port 9191
	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_client_protocol http
#	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_client_key_file /etc/keystone/ssl/private/server01.key
#	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_client_cert_file /etc/keystone/ssl/certs/server01.crt
#	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_client_ca_file /etc/keystone/ssl/certs/ca.crt
#	openstack-config --set /etc/glance/glance-api.conf DEFAULT registry_client_insecure True
fi
openstack-config --set /etc/glance/glance-api.conf keystone_authtoken auth_protocol ${HTTP_CMD}
openstack-config --set /etc/glance/glance-api.conf DEFAULT bind_port 9293
openstack-config --set /etc/glance/glance-registry.conf DEFAULT bind_port 9192
openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken auth_host ${openstack_controller_vip}
openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken auth_protocol ${HTTP_CMD}
openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken admin_user glance
openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken admin_tenant_name service
openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken admin_password $GLANCE_KSPASS
cp /usr/share/glance/glance-api-dist-paste.ini /etc/glance/glance-api-paste.ini
cp /usr/share/glance/glance-registry-dist-paste.ini /etc/glance/glance-registry-paste.ini
cat << EOF >> /etc/glance/glance-api-paste.ini
[filter:authtoken] 
paste.filter_factory=keystoneclient.middleware.auth_token:filter_factory 
auth_host=openstack_controller_vip
admin_user=glance
admin_tenant_name=service
admin_password=glance_keystone_password
EOF

sed -i "s/openstack_controller_vip/${openstack_controller_vip}/" /etc/glance/glance-api-paste.ini
sed -i "s/glance_keystone_password/$GLANCE_KSPASS/" /etc/glance/glance-api-paste.ini

[ `${KEYSTONE_CMD} service-list | grep glance | wc -l` -lt 1 ] && ${KEYSTONE_CMD} service-create --name=glance --type=image --description="Glance Image Service" 
GLANCE_SERVICE_ID=`${KEYSTONE_CMD} service-list | grep -i glance|awk '{print $2}'`
[ `${KEYSTONE_CMD} endpoint-list | grep $GLANCE_SERVICE_ID | wc -l ` -lt 1 ] && ${KEYSTONE_CMD} endpoint-create --service-id=`${KEYSTONE_CMD} service-list|grep glance|awk '{print $2}'` --publicurl=${HTTP_CMD}://${openstack_controller_vip}:9292/v2 --internalurl=${HTTP_CMD}://${openstack_controller_vip}:9292/v2 --adminurl=${HTTP_CMD}://${openstack_controller_vip}:9292/v2 
chown -R glance:glance /var/run/glance;chown -R glance:glance /var/lib/glance;chown -R glance:glance /var/log/glance

##
# Rabbit MQ
##
if [[ -f rabbitmq/rabbitmq.config.controller ]]; then
        /bin/cp -f rabbitmq/rabbitmq.config.controller /etc/rabbitmq/rabbitmq.config
	first_openstack_controller_host=`fgrep ${first_openstack_controller} /etc/hosts| grep -v ^#| awk '{print $2}'|cut -d\. -f1|head -1`
	second_openstack_controller_host=`fgrep ${second_openstack_controller} /etc/hosts| grep -v ^#| awk '{print $2}'|cut -d\. -f1|head -1`
	third_openstack_controller_host=`fgrep ${third_openstack_controller} /etc/hosts| grep -v ^#| awk '{print $2}'|cut -d\. -f1|head -1`
        sed -i "s/first_openstack_controller/${first_openstack_controller_host}/" /etc/rabbitmq/rabbitmq.config
        sed -i "s/second_openstack_controller/${second_openstack_controller_host}/" /etc/rabbitmq/rabbitmq.config
        sed -i "s/third_openstack_controller/${third_openstack_controller_host}/" /etc/rabbitmq/rabbitmq.config
fi

[[ -f rabbitmq/.erlang.cookie ]] && { /bin/cp -p rabbitmq/.erlang.cookie /var/lib/rabbitmq/.erlang.cookie; chmod 0400 /var/lib/rabbitmq/.erlang.cookie; chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie; }
service rabbitmq-server stop
[[ `ps -ef | grep rabbitmq|wc -l` -gt 0 ]] && kill -9 `ps -ef | grep rabbit| grep -v grep| awk '{print $2}'`
/usr/sbin/rabbitmq-server --detached &
sleep 2
/usr/sbin/rabbitmqctl stop_app
[[ ! ${first_openstack_controller} == ${local_controller} ]] && /usr/sbin/rabbitmqctl join_cluster rabbit@`fgrep ${first_openstack_controller} /etc/hosts| grep -v ^#| awk '{print $2}'|cut -d\. -f1|head -1`
/usr/sbin/rabbitmqctl start_app
[[ ${first_openstack_controller} == ${local_controller} ]] &&  /usr/sbin/rabbitmqctl set_policy cluster-all-queues '^(?!amq\.).*' '{"ha-mode":"all","ha-sync-mode":"automatic"}'

###
# SSL fix for dashboard by Sanju
###
[[ -f ./glance/http.py ]] && /bin/cp -p ./glance/http.py /usr/lib/python2.6/site-packages/glanceclient/common

####
# Restart
####
#service haproxy restart
service openstack-glance-api restart
service openstack-glance-registry restart 
chkconfig openstack-glance-api on
chkconfig openstack-glance-registry on
