#!/bin/bash
set -x
function usage() {
cat <<EOF
usage: $0 options

This script will install openstack components on a controller node

Example:
        openstack_install.sh [-L] -v openstack_controller_vip   -c contrail_controller_vip  -F first_openstack_controller -S second_openstack_controller -T third_openstack_controller [ -e glusterfs_vip] [-m glusterfs_volume_name]

OPTIONS:
  -c -- Contrail conreoller IP
  -h -- Help Show this message
  -g -- Glance Mysql password
  -G -- Glance Keystone password
  -F -- The first openstack controller's IP address
  -L -- Use SSL for Keystone
  -e -- Glusterfs VIP
  -m -- Gluasterfs mount point volume name
  -n -- NOVA Mysql password
  -N -- NOVA Keystone password
  -r -- Repo server name or IP
  -R -- Mysql Root password
  -S -- The second openstack controller's IP address
  -T -- The thirdopenstack controller's IP address
  -u -- Neutron Mysql password
  -U -- Neutron Keystone password
  -V -- Verbose Verbose output
  -v -- VIP of the openstack controller

EOF
}
FIRST_CONTROLLER=""
SSL_FLAG=""
glusterfs_vip=""
glusterfs_vol=""
HTTP_CMD="http"
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
[[ $# -lt 2 ]] && { usage; exit 1; }
while getopts "c:hg:G:F:Ln:N:r:R:S:T:u:U:v:e:m:VD" OPTION; do
case "$OPTION" in
c)
	contrail_controller=`grep "${OPTARG}\s" /etc/hosts | grep -v ^#|head -1|awk '{print $1}'`
	;;
h)
        usage
        exit 0
        ;;
e)
	glusterfs_vip="$OPTARG"
	;;
m)
	glusterfs_vol="$OPTARG"
	;;
g)
        GLANCE_DBPASS="$OPTARG"
        ;;
G)
        GLANCE_KSPASS="$OPTARG"
        ;;
F)
        FIRST_CONTROLLER=`grep "${OPTARG}\s" /etc/hosts | grep -v ^#|head -1|awk '{print $1}'`
        ;;
L)	SSL_FLAG="-L"
	;;
n)
        NOVA_DBPASS="$OPTARG"
        ;;
N)
        NOVA_KSPASS="$OPTARG"
        ;;
r)
	REPO_SERVER="$OPTARG"
	;;
R)
        MYSQL_ROOT_PASS="$OPTARG"
        ;;
S)
        SECOND_CONTROLLER=`grep "${OPTARG}\s" /etc/hosts | grep -v ^#|head -1|awk '{print $1}'`
        ;;
T)
        THIRD_CONTROLLER=`grep "${OPTARG}\s" /etc/hosts | grep -v ^#|head -1|awk '{print $1}'`
        ;;
v)
        controller=`grep "${OPTARG}\s" /etc/hosts | grep -v ^#|head -1|awk '{print $1}'`
        ;;
V)
        display_version
        exit 0
        ;;
u)
        NEUTRON_DBPASS="$OPTARG"
        ;;
U)
        NEUTRON_KSPASS="$OPTARG"
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

local_controller=`egrep $HOSTNAME /etc/hosts|grep -v ^#|head -1|awk '{print $1}'`
if [[  ${FIRST_CONTROLLER} == ${local_controller}  ]]; then
	ADMIN_PASS=${ADMIN_PASS:-$(openssl rand -hex 10)}
	contAdmin_PASS=${contAdmin_PASS:-$(openssl rand -hex 10)}
	KEYSTONE_DBPASS=${KEYSTONE_DBPASS:-$(openssl rand -hex 10)}
	GLANCE_DBPASS=${GLANCE_DBPASS:-$(openssl rand -hex 10)}
	NOVA_DBPASS=${NOVA_DBPASS:-$(openssl rand -hex 10)}
	GLANCE_KSPASS=${GLANCE_KSPASS:-$(openssl rand -hex 10)}
	NOVA_KSPASS=${NOVA_KSPASS:-$(openssl rand -hex 10)}
	NEUTRON_KSPASS=${NEUTRON_KSPASS:-$(openssl rand -hex 10)}
	MYSQL_ROOT_PASS=${MYSQL_ROOT_PASS:-$(openssl rand -hex 10)}
	ADMIN_TOKEN=$(openssl rand -hex 10)
	local_controller=`egrep $HOSTNAME /etc/hosts|grep -v ^#|head -1|awk '{print $1}'`
	controller=${controller:-"${local_controller}"}
	contrail_controller=${contrail_controller:-"$controller"}
	[[ -f ./.keystone_grants ]] && rm -f ./.keystone_grants
	#NODE_INDEX="-F"
	#[[ ${FIRST_CONTROLLER} == 0 ]] && NODE_INDEX="-S"
	echo "#Keystone grants created on `date`" >> ./.keystone_grants
	echo "SSL_FLAG=${SSL_FLAG}">>./.keystone_grants
	echo "ADMIN_KSPASS=${ADMIN_PASS}" >> ./.keystone_grants
	echo "KEYSTONE_DBPASS=${KEYSTONE_DBPASS}" >> ./.keystone_grants
	echo "NEUTRON_KSPASS=${NEUTRON_KSPASS}" >> ./.keystone_grants
	echo "NOVA_KSPASS=${NOVA_KSPASS}" >> ./.keystone_grants
	echo "NOVA_DBPASS=${NOVA_DBPASS}" >> ./.keystone_grants
	echo "GLANCE_KSPASS=${GLANCE_KSPASS}" >> ./.keystone_grants
	echo "GLANCE_DBPASS=${GLANCE_DBPASS}" >> ./.keystone_grants
	echo "MYSQL_ROOT_PASS=${MYSQL_ROOT_PASS}" >> ./.keystone_grants
	echo "openstack_controller=${controller}" >> ./.keystone_grants
	echo "contrail_controller=${contrail_controller}" >> ./.keystone_grants
	echo "OS_SERVICE_TOKEN=${ADMIN_TOKEN}"  >> ./.keystone_grants
	echo "contAdmin_PASS=${contAdmin_PASS}"  >> ./.keystone_grants
else
	###
        # Get Keys
        ###
        [[ -f .keystone_grants ]] && { rm -rf .keystone_grants; rm -rf keystone_grants.enc; }
        curl --insecure -o keystone_grants.enc https://${FIRST_CONTROLLER}/.tmp/keystone_grants.enc
	[[  -f keystone/newkey.pem && -f keystone_grants.enc ]] && openssl rsautl -decrypt -inkey keystone/newkey.pem -in keystone_grants.enc -out .keystone_grants
	[[ ! -f  ./.keystone_grants ]] && { echo "Require credential file from Openstacl installation!"; exit 1; }
        ADMIN_KSPASS=${ADMIN_KSPASS:-`cat ./.keystone_grants|grep -i ADMIN_KSPASS| grep -v ^#|cut -d= -f2`}
        contAdmin_PASS=${contAdmin_PASS:-`cat ./.keystone_grants|grep -i contAdmin_PASS| grep -v ^#|cut -d= -f2`}
        KEYSTONE_DBPASS=${KEYSTONE_DBPASS:-`cat ./.keystone_grants|grep -i KEYSTONE_DBPASS| grep -v ^#|cut -d= -f2`}
        GLANCE_DBPASS=${GLANCE_DBPASS:-`cat ./.keystone_grants|grep -i GLANCE_DBPASS| grep -v ^#|cut -d= -f2`}
        NOVA_DBPASS=${NOVA_DBPASS:-`cat ./.keystone_grants|grep -i NOVA_DBPASS| grep -v ^#|cut -d= -f2`}
        GLANCE_KSPASS=${GLANCE_KSPASS:-`cat ./.keystone_grants|grep -i GLANCE_KSPASS| grep -v ^#|cut -d= -f2`}
        NOVA_KSPASS=${NOVA_KSPASS:-`cat ./.keystone_grants|grep -i NOVA_KSPASS| grep -v ^#|cut -d= -f2`}
        NEUTRON_KSPASS=${NEUTRON_KSPASS:-`cat ./.keystone_grants|grep -i NEUTRON_KSPASS| grep -v ^#|cut -d= -f2`}
        MYSQL_ROOT_PASS=${MYSQL_ROOT_PASS:-`cat ./.keystone_grants|grep -i MYSQL_ROOT_PASS| grep -v ^#|cut -d= -f2`}
        ADMIN_TOKEN=${ADMIN_TOKEN:-`cat ./.keystone_grants|grep -i ADMIN_TOKEN| grep -v ^#|cut -d= -f2`}
	controller=${controller:-`cat ./.keystone_grants|grep -i openstack_controller| grep -v ^#|cut -d= -f2`}
	contrail_controller=${contrail_controller:-`cat ./.keystone_grants|grep -i contrail_controller| grep -v ^#|cut -d= -f2`}
fi

####
# Clean up 
####
for file_n in keystone glance nova mysql
do
    [[ /data/var/lib/${file_n} ]] && rm -fr /data/var/lib/${file_n}
    [[ /var/lib/${file_n} ]] && rm -fr /var/lib/${file_n}
    [[ /data/var/log/${file_n} ]] && rm -fr /data/var/log/${file_n} 
    [[ /var/log/${file_n} ]] && rm -fr /var/log/${file_n}
done
umount -f `df -k|grep glance|awk '{print $1}'` > /dev/null 2>&1

##
# Open up iptables
##
iptables -A INPUT -p tcp --dport 5672:5673 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables-save
service iptables stop

###
# Install haproxy and keepalived
###
[[ -f ./ha_install.sh ]] && ./ha_install.sh ${SSL_FLAG} -v $controller -F ${FIRST_CONTROLLER} -S ${SECOND_CONTROLLER} -T ${THIRD_CONTROLLER}
[[ $? -ne 0 ]] && { echo "Install HA failure, Abort!!!"; exit 1; }
##
# Install keystone
##
[[ -f ./keystone_install.sh ]] && ./keystone_install.sh  ${SSL_FLAG} -v $controller -F ${FIRST_CONTROLLER} -S ${SECOND_CONTROLLER} -T ${THIRD_CONTROLLER} -t ${KEYSTONE_DBPASS}
[[ $? -ne 0 ]] && { echo "Install Keystone failure, Abort!!!"; exit 1; }
##
# Install glance
##
[[ -f ./glance_install.sh ]] && ./glance_install.sh  ${SSL_FLAG} -v $controller -F ${FIRST_CONTROLLER} -S ${SECOND_CONTROLLER} -T ${THIRD_CONTROLLER}
[[ $? -ne 0 ]] && { echo "Install Glance failure, Abort!!!"; exit 1; }
##
# Install nova
##
[[ -f ./nova_install.sh ]]  && ./nova_install.sh  ${SSL_FLAG} -v $controller -c ${contrail_controller} -F ${FIRST_CONTROLLER} -S ${SECOND_CONTROLLER} -T ${THIRD_CONTROLLER}
[[ $? -ne 0 ]] && { echo "Install Nova failure, Abort!!!"; exit 1; }
##
# Install neutron endpoint
##
[[ -f ./neutron_install.sh ]]  && ./neutron_install.sh  ${SSL_FLAG} -v ${contrail_controller} -F ${FIRST_CONTROLLER}
[[ $? -ne 0 ]] && { echo "Install Neutron failure, Abort!!!"; exit 1; }
###
# Install Horizon
###
[[ -f ./horizon_install.sh ]]  && ./horizon_install.sh   ${SSL_FLAG} -v ${controller} -F ${FIRST_CONTROLLER}
[[ $? -ne 0 ]] && { echo "Install Horizon failure, Abort!!!"; exit 1; }
###
# Pass credential
###
[[ -f keystone/newpub.pem && ${FIRST_CONTROLLER} == ${local_controller} ]] && openssl rsautl -encrypt -pubin -inkey keystone/newpub.pem -in ./.keystone_grants -out keystone_grants.enc
if [[ -d /var/www/html && ${FIRST_CONTROLLER} == ${local_controller} ]]; then
	mkdir -p /var/www/html/.tmp
	[[ -f /var/www/html/.tmp/keystone_grants.enc ]] && rm -f /var/www/html/.tmp/keystone_grants.enc
	[[ -f keystone_grants.enc ]] && /bin/cp -pf keystone_grants.enc /var/www/html/.tmp/
	cd /etc/keystone
	tar cpf keystone_ssl.tar ssl
	openssl enc -aes-256-cfb -kfile /var/lib/rabbitmq/.erlang.cookie -in keystone_ssl.tar -out /var/www/html/.tmp/keystone_ssl.tar.enc 
	[[ -f keystone_ssl.tar ]] &&  rm -f keystone_ssl.tar
	cd - 
else
	curl --insecure -o keystone_ssl.tar.enc https://${FIRST_CONTROLLER}/.tmp/keystone_ssl.tar.enc
	openssl enc -aes-256-cfb -d -kfile /var/lib/rabbitmq/.erlang.cookie -in keystone_ssl.tar.enc -out /etc/keystone/keystone_ssl.tar
	cd /etc/keystone
	mv ./ssl ./ssl.orig
	[[ -f keystone_ssl.tar ]] && tar xpf keystone_ssl.tar
	i[[ -f keystone_ssl.tar ]] && rm -f keystone_ssl.tar
	cd - 
fi
if [[ -f .keystone_grants ]]; then
	[[ ! -d /var/www/html/.tmp ]] && { mkdir -p /var/www/html/.tmp; /bin/cp -p ./keystone_grants.enc /var/www/html/.tmp/; }
	rm -f ./keystone_grants.enc
	rm -f .keystone_grants
fi

##
# Add space 
#
[[ ! -d /data && `grep vda2 /etc/fstab|wc -l` -lt 1 ]] && echo "/dev/vda2  /data   ext4    defaults    0 0" >> /etc/fstab
[[ ! -d /data ]] && mkdir -p /data
if [[ ! -e /dev/vda2 && -e /dev/vda ]]; then
        (echo n; echo p;echo 2; echo; echo +50G;echo w;echo q)| fdisk /dev/vda
        partx -v -a /dev/vda
        mkfs -t ext4 /dev/vda2
fi
[[ ! -e /data/lost+found ]] && mount /data
[[ -d /data/var/lib ]] && rm -rf /data/var/lib
[[ -d /data/var/log ]] && rm -rf /data/var/log
service rabbitmq-server stop 
[[ `ps -ef| grep epmd|grep -v grep|wc -l` -gt 0 ]] && pkill epmd
sleep 1
[[ `ps -ef| grep epmd|grep -v grep|wc -l` -gt 0 ]] && kill -9 `ps -ef| grep epmd|grep -v grep| awk '{print $2}'`
[[ -d /var/lib/rabbitmq/mnesia ]] && rm -rf /var/lib/rabbitmq/mnesia

service mysql stop
service httpd stop
service keepalived stop
service haproxy stop
service openstack-keystone stop
service openstack-glance-api stop
service openstack-glance-registry stop
service openstack-nova-api stop
service openstack-nova-cert stop
service openstack-nova-conductor stop
#service openstack-nova-console stop
service openstack-nova-consoleauth stop
service openstack-nova-novncproxy stop
service openstack-nova-scheduler stop
service openstack-nova-compute stop
if [[ ! -d /data/var/lib ]]; then
        mkdir -p /data/var/lib
	for file_n in keystone nova mysql
        do
        	mv -f /var/lib/${file_n} /data/var/lib
        	ln -sf /data/var/lib/${file_n} /var/lib/${file_n}
	done
fi
if [[ ! -d /data/var/log ]]; then
        mkdir -p /data/var/log
	for file_n in keystone glance nova
	do
        	mv -f /var/log/${file_n} /data/var/log
        	ln -sf /data/var/log/${file_n} /var/log/${file_n}
	done
fi

####
# Enable shared glance volume based on glusterfs
##
if [[ ! -z ${glusterfs_vip} && ! -z ${glusterfs_vol} ]]; then
	[[ `rpm -qa | grep glusterfs|wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa | grep glusterfs`
	yum -y install --disablerepo=* --enablerepo=havana_install_repo110 glusterfs glusterfs-fuse glusterfs-rdma
	[[ $? -ne 0 ]] && { echo "Install glusterfs client failed!"; exit 1; }
	[[ -d /var/lib/glance ]] && rm -rf /var/lib/glance
	mkdir -p /var/lib/glance
	mount -t glusterfs ${glusterfs_vip}:/${glusterfs_vol} /var/lib/glance
	[[ $? -ne 0 ]] && { echo "Mount glusterfs server failed!"; exit 1; }
	[[ ! -d /var/lib/glance/images ]] && { mkdir -p /var/lib/glance/images; chown -R glance:glance /var/lib/glance; }
else
	mv -f /var/lib/glance /data/var/lib
	ln -sf /data/var/lib/glance /var/lib/glance
fi


##
# Start services
## 
service rabbitmq-server start 
if [[ ${local_controller} == ${FIRST_CONTROLLER} ]]; then
	/etc/init.d/mysql restart --wsrep_cluster_address="gcomm://"
	/usr/sbin/rabbitmqctl set_policy cluster-all-queues '^(?!amq\.).*' '{"ha-mode":"all","ha-sync-mode":"automatic"}'
else
	/etc/init.d/mysql restart
fi
service httpd start
service keepalived start
service haproxy start
service openstack-keystone start
service openstack-glance-api start
service openstack-glance-registry start
service openstack-nova-api start
service openstack-nova-cert start
service openstack-nova-conductor start
#service openstack-nova-console start
service openstack-nova-consoleauth start
service openstack-nova-novncproxy start
service openstack-nova-scheduler start
service openstack-nova-compute start
service iptables stop
