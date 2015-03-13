#!/bin/bash
set -x 
function usage() {
cat <<EOF
usage: $0 options

This script will install Contrail and Neutron components on a single-node SDN controller

Example:
        contrasl_neutron_install.sh [-L] -o openstack_controller -F 1st_contrail_controller -S 2nd_contrail_controller -T 3rd_contrail_controller [-n router_asn_num]

OPTIONS:
  -h -- Help Show this message
  -F -- The first contrail controller's IP address
  -m -- Neutron keystoen password 
  -L -- Use SSL for Keystone
  -M -- Neutron Database password
  -R -- Repo server nmae of IP
  -S -- The second contrail controller's IP address
  -t -- Admin keystone initial token 
  -T -- The third contrail controller's IP address
  -n -- Router ASN number, Default is 64512
  -V -- Version Output the version of this script

EOF
}

mask2cidr() {
    nbits=''
    IFS=.
    for dec in $1 ; do
        case $dec in
            255) let nbits+=8;;
            254) let nbits+=7;;
            252) let nbits+=6;;
            248) let nbits+=5;;
            240) let nbits+=4;;
            224) let nbits+=3;;
            192) let nbits+=2;;
            128) let nbits+=1;;
            0);;
            *) echo "Error: $dec is not recognised"; exit 1
        esac
    done
    echo "$nbits"
}

NEW_INSTALL=0;UPGRADE=0
router_asn_num=64512
KEYSTONE_CMD=keystone
HTTP_CMD=http
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
[[ $# -lt 4 ]] && { usage; exit 1; }

while getopts "ho:F:Lm:M:R:S:t:T:v:V:D" OPTION; do
case "$OPTION" in
h)
        usage
        exit 0
        ;;
o)
        openstack_controller="$OPTARG"
	[[ ! ${openstack_controller} ]] && { usage; exit 1; }
        ;;
F)
        first_contrail_controller_name="$OPTARG"
        ;;
L)
	HTTP_CMD=https
	SSL_FLAG="-L"
	KEYSTONE_CMD="keystone --insecure"
	;;
m)
        NEUTRON_KSPASS="$OPTARG"
        ;;
M)
        NEUTRON_DBPASS="$OPTARG"
        ;;
R)
        REPO_SERVER="$OPTARG"
        ;;
S)
        second_contrail_controller_name="$OPTARG"
        ;;
t)
        admin_ks_init_token="$OPTARG"
	[[ ! ${admin_ks_init_token} ]] && { usage; exit 1; }
        ;;
T)
        third_contrail_controller_name="$OPTARG"
        ;;
n)
        router_asn_num="$OPTARG"
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

#[[ ! ${openstack_controller_name} ]] && { Usage; exit 1; }
#openstack_controller=`fgrep ${openstack_controller_name} /etc/hosts|grep -vi ^None|awk '{print $1}'`
###
# Get keys
##
[[ -f .keystone_grants ]] && rm -rf .keystone_grants
curl --insecure -o keystone_grants.enc https://${openstack_controller}/.tmp/keystone_grants.enc
[[  -f keystone/newkey.pem && -f keystone_grants.enc ]] && openssl rsautl -decrypt -inkey keystone/newkey.pem -in keystone_grants.enc -out .keystone_grants
[[ $? -ne 0 ]] && { echo "Key decryption failed!"; exit 1; }
[[ ! -f  ./.keystone_grants ]] && { echo "Require credential file from Openstacl installation!"; exit 1; }

NEUTRON_DBPASS=${NEUTRON_DBPASS:-`cat ./.keystone_grants|grep NEUTRON_DBPASS| grep -v ^#|cut -d= -f2`}
NEUTRON_KSPASS=${NEUTRON_KSPASS:-`cat ./.keystone_grants|grep NEUTRON_KSPASS| grep -v ^#|cut -d= -f2`}
ADMIN_KSPASS=${ADMIN_KSPASS:-`cat ./.keystone_grants|grep ADMIN_KSPASS| grep -v ^#|cut -d= -f2`}
OS_SERVICE_TOKEN=${OS_SERVICE_TOKEN:-`cat ./.keystone_grants|grep OS_SERVICE_TOKEN| grep -v ^#|cut -d= -f2`}
REPO_SERVER=${REPO_SERVER:-`cat ./.keystone_grants|grep -i REPO_SERVER| grep -v ^#|cut -d= -f2`}
SSL_FLAG=${SSL_FLAG:-`cat ./.keystone_grants|grep -i SSL_FLAG| grep -v ^#|cut -d= -f2`}
[[ ${SSL_FLAG} == "-L" ]] && { KEYSTONE_CMD="keystone --insecure"; HTTP_CMD="https"; }
#admin_ks_init_token=${admin_ks_init_token:-`cat ./.keystone_grants|grep -i KEYSTONE_ADMIN_PASS| grep -v ^#|cut -d= -f2`}
sed -i "/^None/d" /etc/hosts
this_ip=`fgrep $HOSTNAME /etc/hosts|grep -vi ^None|awk '{print $1}'`
first_contrail_controller=`fgrep ${first_contrail_controller_name} /etc/hosts|grep -v ^#|head -1|awk '{print $1}'`
second_contrail_controller=`fgrep ${second_contrail_controller_name} /etc/hosts|grep -v ^#|head -1|awk '{print $1}'`
third_contrail_controller=`fgrep ${third_contrail_controller_name} /etc/hosts|grep -v ^#|head -1|awk '{print $1}'`
this_interface=`ls /proc/net/bonding|head -1`
for that_interface in `ls /sys/class/net|egrep -v 'virbr|lo'`; do [[ `cat /sys/class/net/${that_interface}/carrier` -eq 1 ]] &&  break; done
this_interface=${this_interface:-${that_interface}}	
contrail_controller=${this_vip:-`cat ./.keystone_grants|grep -i contrail_controller| grep -v ^#|cut -d= -f2`}	
export OS_AUTH_URL=${HTTP_CMD}://${openstack_controller}:35357/v2.0
export OS_USERNAME=admin
export OS_PASSWORD=${ADMIN_KSPASS}
export OS_TENANT_NAME=admin
export ADMIN_USER=admin
export ADMIN_TENANT=admin
export ADMIN_TOKEN=${ADMIN_KSPASS}
export IFMAP_CONTROL_PASS=${OS_SERVICE_TOKEN}
export IFMAP_DNS_PASS=${NEUTRON_KSPASS}

####
# Space allocation
###
[[ `grep vda2 /etc/fstab|wc -l` -lt 1 ]] && echo "/dev/vda2  /data   ext4    defaults    0 0" >> /etc/fstab
[[ ! -d /data ]] && mkdir -p /data
if [[ ! -e /dev/vda2 && -e /dev/vda ]]; then
        (echo n; echo p;echo 2; echo; echo +50G;echo w;echo q)| fdisk /dev/vda
        partx -v -a /dev/vda
        mkfs -t ext4 /dev/vda2
fi
[[ ! -e /data/lost+found ]] && mount /data

###
# Stop any running Contrail processes
#####
service keepalived stop
service haproxy stop
service neutron-server stop
service neutron-server stop
service supervisor-analytics stop
service supervisor-config stop
service supervisor-control stop
#service supervisor-dns stop
service supervisor-webui stop
service supervisord-contrail-database stop
[[ `ps -ef | grep zookeeper| grep -v grep |wc -l` -gt 0 ]] && kill `ps -ef | grep zookeeper| grep -v grep| awk '{print $2}'`

####
# Clean up
####
for file_n in contrail cassandra zookeeper neutron redis
do
    [[ /data/var/lib/${file_n} ]] && rm -fr /data/var/lib/${file_n}
    [[ /var/lib/${file_n} ]] && rm -fr /var/lib/${file_n}
    [[ /data/var/log/${file_n} ]] && rm -fr /data/var/log/${file_n}
    [[ /var/log/${file_n} ]] && rm -fr /var/log/${file_n}
    [[ /etc/${file_n} ]] && rm -fr /etc/${file_n}
    [[ /data/${file_n} ]] && rm -fr /etc/${file_n}
done

[[ -d ~/keystone-signing ]] && rm -rf ~/keystone-signing


####
# Remove old installations
###
yum -y erase `rpm -qa | egrep -i 'nova|keystine|glance|neutron|contrail|neutron|supervisor|python-keystoneclient|haproxy|cassandra|zookeeper'`; rpm -e --nodeps supervisor redis gmp python-bitarray
for conf_file in /etc/haproxy /etc/keepalived /opt/contrail /home/cassandra /var/lib/cassandra /var/lib/zookeeper /var/lib/redis
do
	rm -rf ${conf_file}
done
[[ `rpm -qa | grep gmp-|wc -l` -lt 1 ]] && yum -y install --disablerepo=* --enablerepo=havana_install_repo gmp
[[ ! -f /usr/lib64/libgmp.so.3 ]] && ln -s /usr/lib64/libgmp.so /usr/lib64/libgmp.so.3
[[ `rpm -qa | grep contrail|wc -l` -lt 1 ]] && yum -y install --disablerepo=* --enablerepo=contrail_install_repo110 contrail-openstack-analytics contrail-openstack-config contrail-openstack-database contrail-openstack-control contrail-openstack-webui supervisor.x86_64 python-novaclient contrail-config redis contrail-web-controller contrail-web-core python-bitarray
[[ $? -ne 0 ]] && { echo "Package install failed on Contrail!"; exit 1; }
[[ `rpm -qa | grep quantum|wc -l` -gt 1 ]] && rpm -e --nodeps `rpm -qa | grep quantum`

####
# Install VRRP and Haproxy
###
[[ `rpm -qa | grep keepalived|wc -l` -gt 0 ]] && rpm -e --nodeps keepalived
[[ `rpm -qa | grep keepalived|wc -l` -lt 1 ]] && yum -y install keepalived
[[ $? -ne 0 ]] &&  { echo "Keepalived package installation failed!"; exit 1; }
[[ `rpm -qa | grep haproxy|wc -l` -gt 0 ]] && rpm -e --nodeps haproxy
yum -y install --disablerepo=* --enablerepo=havana_install_repo keepalived haproxy xinetd
[[ $? -ne 0 ]] &&  { echo "HAproxy/Keepalived/Xinetd package installation failed!"; exit 1; }

####
# Configure VRRP and Haproxy
###
[[ -f keepalived/keepalived.conf.controller ]] && /bin/cp -fp keepalived/keepalived.conf.controller /etc/keepalived/keepalived.conf
[[ ! -d /etc/haproxy ]] && mkdir -p /etc/haproxy
[[ `grep haproxy /etc/passwd | grep -v grep |wc -l` -lt 1 ]] && adduser haproxy
[[ ! -d /var/lib/haproxy ]] && { mkdir -p /var/lib/haproxy; chown -R haproxy:haprox /var/lib/haproxy/; }
[[ ! -d  /etc/contrail/ssl/certs ]] && mkdir -p  /etc/contrail/ssl/certs
[[ -f ./keystone/server01.pem ]] && { /bin/cp -pf ./keystone/server01.pem /etc/contrail/ssl/certs/server01.pem; chmod o-r  /etc/contrail/ssl/certs/server01.pem; }
##
# Temp allow ONLY http. Pending SSL fix
###
[[ -f haproxy/haproxy.cfg.controller && ${HTTP_CMD} == "https"  ]] && /bin/cp -fp haproxy/haproxy.cfg.controller /etc/haproxy/haproxy.cfg
#[[ -f haproxy/haproxy_ssl.cfg.controller && ${HTTP_CMD} == "https"  ]] && /bin/cp -fp haproxy/haproxy_ssl.cfg.controller /etc/haproxy/haproxy.cfg

for conf_file in /etc/keepalived/keepalived.conf  /etc/haproxy/haproxy.cfg
do
        sed -i "s/this_vip/${contrail_controller}/g" ${conf_file}
        sed -i "s/first_contrail_controller/${first_contrail_controller}/g" ${conf_file}
        sed -i "s/second_contrail_controller/${second_contrail_controller}/g" ${conf_file}
        sed -i "s/third_contrail_controller/${third_contrail_controller}/g" ${conf_file}
        this_router=`echo ${contrail_controller} |cut -d\. -f4`
        this_priority=`echo ${contrail_controller} |cut -d\. -f4`
        if [[ ${first_contrail_controller} == ${this_ip} ]]; then
                let "this_priority=255" #Highest posible
                sed -i "s/vrrp_state/MASTER/g" ${conf_file}
        else
                sed -i "s/vrrp_state/BACKUP/g" ${conf_file}
        fi
        sed -i "s/this_router/${this_router}/g" ${conf_file}
        sed -i "s/this_priority/${this_priority}/g" ${conf_file}
        sed -i "s/this_interface/${this_interface}/g" ${conf_file}
        if [[ ${HTTP_CMD} == "https" ]]; then
                sed -i "/mode/ s/KEYSTONE_LB_MODE/tcp/g" ${conf_file}
                SERVER_SSL_PEM="\/etc\/contrail\/ssl\/certs\/server01.pem"
                sed -i "/ssl/ s/SERVER_SSL_PEM/${SERVER_SSL_PEM}/" ${conf_file}
        else
                sed -i "s/KEYSTONE_LB_MODE/http/g" ${conf_file}
        fi

done

##
# Install layer7 monitiroing
##
[[ ! -d /usr/local/bin ]] && mkfir -p /usr/local/bin
ls haproxy/check_*.py | while read aa; do cp -pf $aa /usr/local/bin; done
ls haproxy/check_*.xinetd.d | while read a_line
do
        xinetd_file=$(basename `echo $a_line|cut -d. -f1`)
        cp -fp $a_line /etc/xinetd.d/${xinetd_file}
        chmod go-r /etc/xinetd.d/${xinetd_file}
        service_port=`grep port $a_line | grep -v ^#|cut -d= -f2|tr -d ' '`
        service_name=`grep service $a_line | grep -v ^#|awk '{print $2}'`
        #[[ -z ${service_name} ||  -z ${service_port} ]] && continue
        [[ `grep ${service_name} /etc/services |grep -v ^#|wc -l` -lt 1 ]] && echo -e ${service_name} '\t' ${service_port}/tcp '\t\t' "#Haproxy Layer 7 health check" >> /etc/services
        sed -i "/server/ s/${service_name}_port/${service_port}/g" /etc/haproxy/haproxy.cfg
done
iptables -p vrrp -A INPUT -j ACCEPT
iptables -p vrrp -A OUTPUT -j ACCEPT
chkconfig haproxy on
chkconfig keepalived on
service xinetd restart
service keepalived restart
service haproxy restart

###
# Configure System Parameters
###
if [[ `grep fs.file-max /etc/sysctl.conf | grep -v ^# | grep 65535|wc -l` -lt 1 ]]; then
cat << EOF >> /etc/sysctl.conf
net.ipv4.ip_forward=1
net.ipv4.conf.all.rp_filter=0
net.ipv4.conf.default.rp_filter=0
fs.file-max = 65535
EOF
fi
if [[ `grep nproc /etc/security/limits.conf |grep -v ^#| grep 65535|wc -l` -lt 1 ]]; then
cat << EOF >> /etc/security/limits.conf
root soft nproc 65535
* hard nofile 65535
* soft nofile 65535
* hard nproc 65535
* soft nofile 65535
EOF
fi
sysctl -p

###
# Start redis
###
[[ -f /etc/redis.conf ]] && sed -i "/^bind/ s/^bind/#bind/" /etc/redis.conf
[[ ! -d /var/lib/redis ]] && { mkdir -p /var/lib/redis; chown redis:redis /var/lib/redis; }
[[ ! -d /var/log/redis ]] && { mkdir -p /var/log/redis; chown redis:redis /var/log/redis; }
service redis restart

####
# Config Contrail Database
####
zookeeper_ip_list="${first_contrail_controller} ${second_contrail_controller} ${third_contrail_controller}"
cassandra_ip_list="${first_contrail_controller} ${second_contrail_controller} ${third_contrail_controller}"

if [[ ${this_ip} == ${first_contrail_controller} ]]; then
	database_index=1
	redis_role="master"
elif [[ ${this_ip} == ${second_contrail_controller} ]]; then
	database_index=2
elif [[ ${this_ip} == ${third_contrail_controller} ]]; then
	database_index=3
else
	datbase_index=0
fi

#Install basic packages 
yum -y --disablerepo=* --enablerepo=contrail_install_repo110 install contrail-setup contrail-fabric-utils python-pip
pip-python install /opt/contrail/contrail_installer/contrail_setup_utils/pycrypto-2.6.tar.gz
pip-python install /opt/contrail/contrail_installer/contrail_setup_utils/paramiko-1.11.0.tar.gz
pip-python install /opt/contrail/contrail_installer/contrail_setup_utils/Fabric-1.7.0.tar.gz

[[ ! -d /data/cassandra/ContrailAnalytics ]] && mkdir -p /data/cassandra/ContrailAnalytics

####
# Config Contrail Database
####

[[ -f ./utils/setup-vnc-database.py ]] && ./utils/setup-vnc-database.py --self_ip ${this_ip} \
        --data_dir /data/cassandra --dir /usr/share/cassandra --analytics_data_dir /var/lib/analytics/data --cfgm_ip ${this_ip}  --zookeeper_ip_list "${zookeeper_ip_list}" \
        --ssd_data_dir  /var/lib/analytics/ssd_data --initial_token 0 --seed_list "${first_contrail_controller} ${second_contrail_controller}" --database_index ${database_index}

if [[ ${this_ip} == ${third_contrail_controller} ]]; then
	#verify	 database
	echo "verify database"	
fi

####
# Config Contrail Analytics/Collector, TTL unit is in hours. This internal_vip is contrail VIP.
####
[[ -f ./utils/setup-vnc-collector.py ]] && ./utils/setup-vnc-collector.py --cassandra_ip_list  "${cassandra_ip_list}" \
            --cfgm_ip  ${contrail_controller} --self_collector_ip  ${this_ip} --num_nodes 3 \
            --analytics_data_ttl 48 --internal_vip ${contrail_controller} 

####
# Config Contrail Config. This internal_vip is 
####
[[ -f ./utils/setup-vnc-cfgm.py ]] && ./utils/setup-vnc-cfgm.py --self_ip ${this_ip} --keystone_ip ${openstack_controller} \
            --keystone_auth_protocol ${HTTP_CMD} --keystone_insecure True --keystone_auth_port 35357 --keystone_admin_token ${OS_SERVICE_TOKEN} \
            --collector_ip ${this_ip} --service_token ${NEUTRON_KSPASS} --quantum_port 9697 \
            --cassandra_ip_list "${cassandra_ip_list}"  --amqp_server_ip ${openstack_controller} \
            --zookeeper_ip_list "${zookeeper_ip_list}" --manage_neutron no \
            --multi_tenancy --internal_vip ${contrail_controller} --region_name RegionOne \
            --nworkers 1

####
# Config Contrail Control 
####
[[ -f ./utils/setup-vnc-control.py ]] &&  ./utils/setup-vnc-control.py --cfgm_ip ${contrail_controller}  --collector_ip ${this_ip} \
            --discovery_ip ${this_ip} --self_ip ${this_ip}
####
# Config Contrail Web UI
####
[[ -f ./utils/setup-vnc-webui.py ]] && ./utils/setup-vnc-webui.py --cfgm_ip ${contrail_controller} \
	--openstack_ip ${openstack_controller} --contrail_internal_vip ${contrail_controller} \
        --collector_ip ${this_ip}  --cassandra_ip_list "${cassandra_ip_list}"  --keystone_auth_protocol ${HTTP_CMD} \
	--keystone_ip  ${openstack_controller}

###
# Temp fixes for v1.1
###
[[ -f /etc/contrail/contrail-api.conf ]] && sed -i "/^rabbit_server/ s/=.*/=${openstack_controller}/" /etc/contrail/contrail-api.conf
[[ -f  /usr/lib/python2.6/site-packages/neutron/service.py ]] && sed -i "/cls.create/ s/quantum/neutron/"  /usr/lib/python2.6/site-packages/neutron/service.py
[[ ${this_ip} == ${first_contrail_controller} ]] && keystone --insecure user-password-update --pass ${NEUTRON_KSPASS} neutron

####
# Temp patches
####
[[ -f  patches/vnc_api.py ]] && /bin/cp -pf patches/vnc_api.py /usr/lib/python2.6/site-packages/vnc_api/.
[[ -f  patches/vnc_auth_keystone.py ]] && /bin/cp -pf patches/vnc_auth_keystone.py /usr/lib/python2.6/site-packages/vnc_cfg_api_server/.
[[ -f  patches/greenio.py ]] && /bin/cp -pf patches/greenio.py /usr/lib/python2.6/site-packages/eventlet/.
[[ -f  patches/contrail_plugin.py ]] && /bin/cp -pf patches/contrail_plugin.py /usr/lib/python2.6/site-packages/neutron_plugin_contrail/plugins/opencontrail/contrail_plugin.py

###
# Stop all services
###
chkconfig redis on
service redis stop
chkconfig zookeeper on
service zookeeper stop
chkconfig supervisor-analytics on
service supervisor-analytics stop
chkconfig supervisor-config on
service supervisor-config stop
chkconfig supervisor-control on
service supervisor-control stop
service keepalived stop
service haproxy stop
chkconfig supervisor-webui on
service supervisor-webui stop
chkconfig supervisord-contrail-database on
service supervisord-contrail-database stop
chkconfig neutron-server on
service neutron-server stop
chkconfig rabbitmq-server off
service rabbitmq-server stop
[[ `ps -ef | grep epmd | wc -l` -gt 0 ]] && pkill epmd

###
# Space allocation
###
[[ ! -d /data/var/lib ]] && mkdir -p /data/var/lib
for file_n in contrail cassandra zookeeper neutron analytics redis haproxy
do
    [[ -d /var/lib/${file_n} ]] && { mv -f /var/lib/${file_n} /data/var/lib; ln -sf /data/var/lib/${file_n} /var/lib/${file_n}; }
done
[[ ! -d /data/var/log ]] && mkdir -p /data/var/log
for file_n in contrail cassandra zookeeper neutron analytics redis
do
    [[ -d /var/log/${file_n} ]] && { mv -f /var/log/${file_n} /data/var/log; ln -sf /data/var/log/${file_n} /var/log/${file_n}; }
done

####
# Start Contrail Controller
####
service keepalived start
service haproxy start
service redis start
service zookeeper start
service supervisor-analytics start
service supervisor-config start
service supervisor-control start
#service supervisor-dns start
service supervisor-webui start
service supervisord-contrail-database start
service neutron-server start

###
# Clean up
###
[[ -f keystone_grants.enc ]] && rm -f keystone_grants.enc
[[ -f .keystone_grants ]] && rm -f .keystone_grants
[[ `rpm -qa | grep rabbitmq-server |wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa | grep rabbitmq`
[[ -d /var/log/rabbitmq ]] && rm -rf /var/log/rabbitmq
[[ -d /var/lib/rabbitmq ]] && rm -rf /var/lib/rabbitmq
[[ -d /etc/rabbitmq ]] && rm -rf /etc/rabbitmq

[[ `rpm -qa | grep openstack-nova |wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa | grep openstack-nova`
[[ -d /var/log/nova ]] && rm -rf /var/log/nova
[[ -d /var/lib/nova ]] && rm -rf /var/lib/nova
[[ -d /etc/nova ]] && rm -rf /etc/nova

###
# Provision Control, BGP and linklocal for metadata service
# Following provisioning only need 1 execution
###
if [[ ${this_ip} == ${third_contrail_controller} ]]; then
	j=1; while [[ $j -lt 30 ]]; do echo "Waiting for API service to be up....."; sleep 3; [[ `lsof -i:8082 |wc -l` -gt 2 ]] && break; let j="$j+1"; done
	[[ -f ./utils/provision_linklocal.py ]] && python ./utils/provision_linklocal.py \
                --api_server_ip ${contrail_controller} \
                --linklocal_service_name metadata \
                --linklocal_service_ip 169.254.169.254  \
                --linklocal_service_port 80 \
		--admin_user admin --admin_password ${ADMIN_KSPASS} \
                --ipfabric_service_ip ${openstack_controller} \
                --ipfabric_service_port 8775 --oper add


	[[ -f ./utils/provision_encap.py ]] && python ./utils/provision_encap.py --admin_user admin --admin_password ${ADMIN_KSPASS} \
				     	--api_server_ip ${contrail_controller} --encap_priority MPLSoUDP,MPLSoGRE,VXLAN  --oper add \
					--api_server_port 8082 --admin_tenant_name admin 

	for host_ip in ${first_contrail_controller}   ${second_contrail_controller}  ${third_contrail_controller}
	do
		[[ -f ./utils/provision_control.py ]] && python ./utils/provision_control.py \
					--host_name  `cat /etc/hosts | grep "^${host_ip}\s"| awk '{print $2}'|cut -d\. -f1` \
                                        --host_ip ${host_ip} \
                                        --router_asn ${router_asn_num} \
                                        --api_server_ip ${contrail_controller} \
                                        --api_server_port 8082 \
                                        --admin_user admin --admin_tenant_name admin --admin_password ${ADMIN_KSPASS} \
                                        --oper add
	done
fi
