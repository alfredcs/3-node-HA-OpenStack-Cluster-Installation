#!/bin/bash
set -x
function usage() {
cat <<EOF
usage: $0 options

This script will install and configure Openstack Nova and Contrail vrouter on a compute node.

Example:
	compute_install.sh [-L] -o openstack_controller [-c contrail_controller] [-p admin_interface_name] [ -i  Data/Ctrl interface name] [ -g Data/Ctrl Gateway ]....

OPTIONS:
  -a -- New installation
  -h -- Help Show this message
  -v -- Verbose Verbose output
  -V -- Version Output the version of this script
  -c -- Contrail controller name or IP
  -o -- Openstack controller name or IP
  -d -- Domain name
  -D -- Work director default /opt/compute-install
  -p -- Admin iterface name i.e. eth1 or bond1
  -i -- Data/Ctrl interface name i.e. eth0 or bond0
  -k -- Vrouter kernel default 2.6.32-358.123.2.openstack.el6.x86_64
  -l -- Nova keystone password
  -L -- Enable SSL for Keystone
  -m -- Keystone password for user Neutron default "passwsord"
  -M -- MuySql password for user Neutron default "passwsord"
  -g -- Data/Ctrl Gateway address if admin interface is specified
  -n -- DNS server address 1
  -N -- DNS server address 2
  -p -- Admin interface name i.e. eth1 or bond1
  -s -- Neutron shared secret default "neutronsucks"

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
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
[[ $# -lt 1 ]] && { usage; exit 1; }
HTTP_CMD=http;SSL_FLAG='';this_interface="";admin_interface="ZZZ";data_gw="";data_interface="YYY";data_ip=""
while getopts "aho:c:d:D:i:k:l:Lm:M:g:n:N:p:s:z:uv:V:D" OPTION; do
case "$OPTION" in
a)
        NEW_INSTALL=1
        ;;
h)
        usage
        exit 0
        ;;
o)
        openstack_controller_name="$OPTARG"
        ;;
c)
        contrail_controller_name="$OPTARG"
        ;;
d)
        this_domainname="$OPTARG"
        ;;
D)
        TOP_DIR="$OPTARG"
        ;;
i)
        data_interface="$OPTARG"
        ;;
k)
        this_kernel="$OPTARG"
        ;;
l)
        NOVA_KSPASS="$OPTARG"
        ;;
L)
        HTTP_CMD="https"
        SSL_FLAG="-L"
        ;;
m)
        NEUTRON_KSPASS="$OPTARG"
        ;;
M)
        NEUTRON_DBPASS="$OPTARG"
        ;;
g)
        data_gw="$OPTARG"
        ;;
n)
        dns_server_1="$OPTARG"
        ;;
N)
        dns_server_2="$OPTARG"
        ;;
p)
        admin_interface="$OPTARG"
        ;;
s)
        neutron_shared_secret="$OPTARG"
        ;;
z)
        this_zone="$OPTARG"
        ;;
u)
        UPGRADE=1
        ;;
v)
        VERBOSE=1
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
        exit 0
        ;;
esac
done
SSL_FLAG=""

###
# Check to resolve IP from /etc/hosts
##
[[ ${openstack_controller_name} ]] && openstack_controller=`fgrep ${openstack_controller_name} /etc/hosts |grep -v ^#|head -1|awk '{print $1}'|head -1`
[[ -z ${openstack_controller} ]] && { echo "Make sure /etc/hosts has entries for Openstack controller and Contrail controller!"; exit 1; }

###
# Get Keys
###
[[ -f .keystone_grants ]] && { rm -rf .keystone_grants; rm -rf eystone_grants.enc; }
curl --insecure -o keystone_grants.enc ${HTTP_CMD}://${openstack_controller}/.tmp/keystone_grants.enc
[[  -f keystone/newkey.pem && -f keystone_grants.enc ]] && openssl rsautl -decrypt -inkey keystone/newkey.pem -in keystone_grants.enc -out .keystone_grants
[[ ! -f  ./.keystone_grants ]] && { echo "Require credential file from Openstacl installation!"; exit 1; }
openstack_controller=${openstack_controller:-`cat ./.keystone_grants|grep -i openstack_controller| grep -v ^#|cut -d= -f2`}
contrail_controller=${contrail_controller:-`cat ./.keystone_grants|grep -i contrail_controller| grep -v ^#|cut -d= -f2`}
NOVA_KSPASS=${NOVA_KSPASS:-`cat ./.keystone_grants|grep -i NOVA_KSPASS| grep -v ^#|cut -d= -f2`}
NOVA_DBPASS=${NOVA_DBPASS:-`cat ./.keystone_grants|grep -i NOVA_DBPASS| grep -v ^#|cut -d= -f2`}
SSL_FLAG=${SSL_FLAG:-`cat ./.keystone_grants|grep -i SSL_FLAG| grep -v ^#|cut -d= -f2`}
NEUTRON_KSPASS=${NEUTRON_KSPASS:-`cat ./.keystone_grants|grep NEUTRON_KSPASS| grep -v ^#|cut -d= -f2`}
ADMIN_KSPASS=${ADMIN_KSPASS:-`cat ./.keystone_grants|grep ADMIN_KSPASS| grep -v ^#|cut -d= -f2`}
OS_SERVICE_TOKEN=${OS_SERVICE_TOKEN:-`cat ./.keystone_grants|grep OS_SERVICE_TOKEN| grep -v ^#|cut -d= -f2`}
TOP_DIR=${TOP_DIR:-`pwd`}
[[ -d /proc/net/bonding ]] && this_interface=`ls /proc/net/bonding|grep -v ${admin_interface}|head -1`
this_interface=${this_interface:-`netstat -rn|grep ^0.0.0.0| awk '{print $8}'`}
this_ip=${this_ip:-`fgrep $HOSTNAME /etc/hosts|grep -v ^#|awk '{print $1}'|head -1`}
if [[ ${data_interface} != "YYY" ]]; then
        data_ip=`ifconfig ${data_interface}| grep inet| grep -v inet6|grep addr|cut -d\: -f2|awk '{print $1}'`
else
        #data_ip=`ifconfig ${this_interface}| grep inet| grep -v inet6|grep addr|cut -d\: -f2|awk '{print $1}'`
	data_ip=${this_ip}
        data_gw=`grep -i gateway /etc/sysconfig/network | cut -d= -f2`
fi

[[ -z ${data_gw} && ! -z ${data_ip} ]] && { echo "Need to define data gateway address normally on MX appliances!" exit 1; } 
[[ ${admin_interface} != "ZZZ" ]] && this_gw=`cat /etc/sysconfig/network-scripts/ifcfg-${this_interface}| grep -i gateway| grep -v ^#| cut -d= -f2`
this_gw=${this_gw:-`cat /etc/sysconfig/network|grep -v ^#| grep -i gateway|cut -d= -f2`}
this_domainname=${this_domainname:-`echo $HOSTNAME|cut -d\. -f2,3,4,5`}
this_kernel=${this_kernel:-`uname -r`}
this_zone=${this_zone:-"nova"}
dns_server_2=`cat /etc/resolv.conf| grep nameserver | grep -v ^#| tail -1| awk '{print $2}'`
dns_server_1=`cat /etc/resolv.conf| grep nameserver | grep -v ^#| head -1| awk '{print $2}'`
neutron_shared_secret=${neutron_shared_secret:-"neutronsucks"}
this_netmask=`ifconfig ${this_interface}| grep -i MASK| awk '{print $4}'| cut -d: -f2`
this_netmask=${this_netmask:-"255.255.255.0"}
this_cidr=$(mask2cidr ${this_netmask})
this_cidr=${this_cidr:-"24"}
[ -f $TOP_DIR/contrc ] && source $TOP_DIR/contrc
export ADMIN_USER=admin
export ADMIN_TENANT=admin
export ADMIN_TOKEN=${ADMIN_KSPASS}

###
#Clean up and install pkgs
###
kernel_version=`uname -r`; p_form=`uname -m`
kernel_plat=`echo ${kernel_version}`|sed "s/\.${p_form}//"
service rpcbind restart
[[ -f /etc/sudoers ]] && sed -i -e '/requiretty/ s/^Defaults/#Defaults/' /etc/sudoers
[[ -f /etc/init.d/openstack-nova-compute ]] && service openstack-nova-compute stop
[[ -f /etc/init.d/supervisor-vrouter ]] && service supervisor-vrouter stop
rpm -e --nodeps `rpm -qa | egrep -i 'contrail|neutron|quantum|qemu-kvm|qemu-img|nova|supervisor|setuptools|libguestfs|glusterfs|python-pycrypto'`
for conf_file in /etc/contrail /etc/nova /data/var/log/contrail /data/var/log/nova /data/var/lib/nova /var/lib/libvirt /var/log/libvirt
do
	rm -rf ${conf_file}
done
[ -f /opt/opseng/sbin/run-chef-client ] && chmod a-x /opt/opseng/sbin/run-chef-client
#[[ `lsmod | grep vrouter|wc -l` -gt 0 ]] && rmmod vrouter 
[[ -f /lib/modules/${kernel_version}/extra/net/vrouter/vrouter.ko ]] && /bin/unlink /lib/modules/${kernel_version}/extra/net/vrouter/vrouter.ko
[[ -f `find /lib/modules -name vrouter.ko| head -1` ]] && rm -f `find /lib/modules -name vrouter.ko| head -1`
[[ -f /etc/sysconfig/network-scripts/ifcfg-vhosts0 ]] && rm -f /etc/sysconfig/network-scripts/ifcfg-vhosts0
[[ -f /etc/sysconfig/network-scripts/ifcfg-${this_interface}.rpmsave ]] && mv -f /etc/sysconfig/network-scripts/ifcfg-${this_interface}.rpmsave /etc/sysconfig/network-scripts/ifcfg-${this_interface}

###
# Install pkgs
###
#yum -y --disablerepo=* --enablerepo=havana_install_repo install gmp
#[[ ! -f /usr/lib64/libgmp.so.3 ]] && ln -s /usr/lib64/libgmp.so /usr/lib64/libgmp.so.3
[[ `rpm -qa | grep contrail-openstack-vrouter|wc -l` -lt 1 ]] && { yum -y --disablerepo=* --enablerepo=contrail_install_repo110 install glusterfs-api glusterfs-libs; yum -y --disablerepo=* --enablerepo=contrail_install_repo110 install contrail-openstack-vrouter contrail-vrouter abrt pyhton-thrift contrail-nova-vif contrail-setup contrail-nodemgr contrail-vrouter-init python-pycrypto; }
[[ $? -ne 0 ]] && exit 1
[[ `rpm -qa | egrep 'python-neutronclient|openstack-nova-compute|openstack-nova-common|python-nova'|wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa | egrep 'python-neutronclient|openstack-nova-compute|openstack-nova-common|python-nova|qemu-kvm|qemu-img'`
yum -y --disablerepo=* --enablerepo=havana_install_repo110 install openstack-nova-compute python-neutronclient openstack-nova-common python-nova python-novaclient
[[ $? -ne 0 ]] && exit 1

##
# Kernel update
##
[[ `rpm -qa |grep kernel|grep ${kernel_plat}|wc -l` -lt 1 ]] && rpm -ivh `ls pkgs/kernel*${kernel_plat}*.rpm`
[[ -f /lib/modules/${kernel_version}/extra/net/vrouter/vrouter.ko ]] && rm -f /lib/modules/${kernel_version}/extra/net/vrouter/vrouter.ko
[[ ! -f  /lib/modules/${kernel_version}/extra/net/vrouter/vrouter.ko ]] && { mkdir -p  /lib/modules/${kernel_version}/extra/net/vrouter; ln -s `find /lib/modules -type f -name vrouter.ko| head -1`  /lib/modules/${kernel_version}/extra/net/vrouter/vrouter.ko; }

##
# Add space 
#
[[ ! -d /data ]] && mkdir -p /data
if [[ ! -e /dev/vda2 && -e /dev/vda ]]; then
	(echo n; echo p;echo 2; echo; echo +50G;echo w;echo q)| fdisk /dev/vda
	partx -v -a /dev/vda
	mkfs -t ext4 /dev/vda2
	[[ `grep vda2 /etc/fstab|wc -l` -lt 1 ]] && echo "/dev/vda2  /data   ext4    defaults	 0 0" >> /etc/fstab
fi
[[ ! -e /data/lost+found ]] && mount /data
[[ -d /data/var/lib ]] && rm -rf /data/var/lib
[[ -d /data/var/log ]] && rm -rf /data/var/log
if [[ ! -d /data/var/lib ]]; then
	mkdir -p /data/var/lib
	mv -f /var/lib/nova /data/var/lib
	ln -sf /data/var/lib/nova /var/lib/nova
	mv -f /var/lib/contrail /data/var/lib
	[[ ! -d /data/var/lib/contrail ]] && mkdir -p /data/var/lib/contrail
	[[ -L /var/lib/contrail ]] && rm -f /var/lib/contrail
        ln -sf /data/var/lib/contrail /var/lib/contrail
fi
if [[ ! -d /data/var/log ]]; then 
        mkdir -p /data/var/log
        mv -f /var/log/nova /data/var/log
        ln -sf /data/var/log/nova /var/log/nova
        mv -f /var/log/contrail /data/var/log
        ln -sf /data/var/log/contrail /var/log/contrail
fi

##
# Sysctl parameter configurations
##
cat << EOF >> /etc/sysctl.conf
net.ipv4.ip_forward=1
net.ipv4.conf.all.rp_filter=0
net.ipv4.conf.default.rp_filter=0
EOF
sysctl -p
chkconfig libvirtd on
chkconfig messagebus on
chkconfig openstack-nova-compute on

##
# Install Contrail vrouter
##
if [[ ${HTTP_CMD} == "https" ]]; then
	[[ -f patches/auth_token.py ]] && { /bin/cp -fp /usr/lib/python2.6/site-packages/keystoneclient/middleware/auth_token.py /usr/lib/python2.6/site-packages/keystoneclient/middleware/auth_token.py.orig; /bin/cp -fp patches/auth_token.py  /usr/lib/python2.6/site-packages/keystoneclient/middleware/auth_token.py; /bin/cp -pf patches/auth_token.py /usr/lib/python2.6/site-packages/keystone/middleware/auth_token.py; }
	[[ -f patches/vnc_api.py ]] && /bin/cp -fp patches/vnc_api.py /usr/lib/python2.6/site-packages/vnc_api/vnc_api.py
	[[ -f patches/provision_vrouter.py ]] && /bin/cp -fp patches/provision_vrouter.py  /opt/contrail/utils/provision_vrouter.py
fi
[[ -f ./contrail_installer/contrail_setup_utils/paramiko-1.11.0.tar.gz ]] && pip-python install ./contrail_installer/contrail_setup_utils/paramiko-1.11.0.tar.gz
[[ -f ./contrail_installer/contrail_setup_utils/Fabric-1.7.0.tar.gz ]] && pip-python install ./contrail_installer/contrail_setup_utils/Fabric-1.7.0.tar.gz
env 
if [[ ! -z ${data_ip} && ! -z ${data_gw} ]]; then
	[[ -f $TOP_DIR/contrail_installer/setup-vnc-vrouter.py ]] && $TOP_DIR/contrail_installer/setup-vnc-vrouter.py --cfgm_ip ${contrail_controller} \
		--keystone_ip ${openstack_controller} --internal_vip ${contrail_controller} \
		--keystone_auth_protocol ${HTTP_CMD} --keystone_insecure True --keystone_auth_port 35357 --external_vip ${contrail_controller} \
		--amqp_server_ip ${openstack_controller} --contrail_internal_vip ${contrail_controller} \
                --self_ip ${this_ip} --service_token ${OS_SERVICE_TOKEN} --ncontrols 3 --non_mgmt_ip ${data_ip} --non_mgmt_gw ${data_gw} --quantum_service_protocol ${HTTP_CMD}
else
	[[ -f $TOP_DIR/contrail_installer/setup-vnc-vrouter.py ]] && $TOP_DIR/contrail_installer/setup-vnc-vrouter.py --cfgm_ip ${contrail_controller} \
                --keystone_ip ${openstack_controller} --internal_vip ${contrail_controller} \
                --keystone_auth_protocol ${HTTP_CMD} --keystone_insecure True --keystone_auth_port 35357 --external_vip ${contrail_controller} \
                --amqp_server_ip ${openstack_controller} --contrail_internal_vip ${contrail_controller} \
                --self_ip ${this_ip} --service_token ${OS_SERVICE_TOKEN} --ncontrols 3 --quantum_service_protocol ${HTTP_CMD}
fi

[[ $? -ne 0 ]] && { echo "Setup vrouter failed!"; exit 1; }

###
# Configure Nova and Contrail
###
[ -f $TOP_DIR/nova_compute/nova.conf.compute ] &&  /bin/cp -fp $TOP_DIR/nova_compute/nova.conf.compute /etc/nova/nova.conf
sed -i "s/nova_keystone_password/$NOVA_KSPASS/g" /etc/nova/nova.conf
sed -i "s/nova_db_password/$NOVA_DBPASS/g" /etc/nova/nova.conf
sed -i "s/openstack_controller/${openstack_controller}/g" /etc/nova/nova.conf
sed -i "s/contrail_controller/${contrail_controller}/g" /etc/nova/nova.conf
sed -i "s/this_ip/${this_ip}/g" /etc/nova/nova.conf
sed -i "s/this_zone/${this_zone}/g" /etc/nova/nova.conf
if [[ ${SSL_FLAG} == "-L" ]]; then
	sed -i "/auth_protocol/ s/http/https/g" /etc/nova/nova.conf
	openstack-config --set /etc/nova/nova.conf keystone_authtoken insecure "True"
	openstack-config --set /etc/nova/nova.conf DEFAULT neutron_api_insecure "True"
	openstack-config --set /etc/nova/nova.conf DEFAULT glance_protocol https
	openstack-config --set /etc/nova/nova.conf DEFAULT glance_api_insecure True
	sed -i "/glance_api_servers/ s/http_cmd/${HTTP_CMD}/" /etc/nova/nova.conf
	sed -i "/neutron_url/ s/http_cmd/${HTTP_CMD}/" /etc/nova/nova.conf
	sed -i "/neutron_admin_auth_url/ s/http_cmd/${HTTP_CMD}/" /etc/nova/nova.conf
	[[ -f patches/greenio.py ]] && { /bin/cp -fp /usr/lib/python2.6/site-packages/eventlet/greenio.py /usr/lib/python2.6/site-packages/eventlet/greenio.py.orig; /bin/cp -fp patches/greenio.py  /usr/lib/python2.6/site-packages/eventlet/greenio.py; }
fi
sed -i "s/neutron_keystone_password/$NEUTRON_KSPASS/g" /etc/nova/nova.conf
sed -i "s/nova_keystone_password/$NOVA_KSPASS/g" /etc/nova/api-paste.ini
openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_type  "qemu"
[[ `cat /proc/cpuinfo| grep '^physical id'|wc -l` -gt 1 ]] && openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_type  "kvm"
sed -i "/metadata_proxy_secret/c\metadata_proxy_secret=`grep metadata_proxy_shared_secret /etc/nova/nova.conf| grep -v ^#| cut -d= -f2`"  /etc/contrail/contrail-vrouter-agent.conf 

###
# Configure vhost0 and additional default components
###
[[ -f ./nova_compute/qemu.conf ]] && cp -p ./nova_compute/qemu.conf /etc/libvirt/qemu.conf
[[ -f /lib/modules/`uname -r`/kernel/net/bridge/bridge.ko ]] && mv  /lib/modules/`uname -r`/kernel/net/bridge/bridge.ko /lib/modules/`uname -r`/kernel/net/bridge/bridge.ko.ORIG
[[ `grep 'install bridge' /etc/modprobe.d/blacklist.conf | wc -l ` -gt 0 ]] && echo "install bridge /bin/false" >> /etc/modprobe.d/blacklist.conf
[[ `grep 'blacklist bridge' /etc/modprobe.d/bridge.conf | wc -l ` -gt 0 ]] && echo "blacklist bridge" >> /etc/modprobe.d/bridge.conf

####
# Configure Bonding if needed
####
if [[ ${this_interface} == "bond0" ]]; then
	sed -i "/BONDING_OPTS/ s/mode=*/mode=802.3ad xmit_hash_policy=layer3+4/" /etc/sysconfig/network-scripts/ifcfg-bond0
	sed -i "/^HWADDR/ s/HWADDR/MACADDR/" /etc/sysconfig/network-scripts/ifcfg-bond0
	sed -i "/^IPADDR/ s/IPADDR/#IPADDR/" /etc/sysconfig/network-scripts/ifcfg-bond0
	sed -i "/^NETMASK/ s/NETMASK/#NETMASK/" /etc/sysconfig/network-scripts/ifcfg-bond0
	sed -i "/^NETWORK/ s/NETWORK/#NETWORK/" /etc/sysconfig/network-scripts/ifcfg-bond0
	sed -i "/^USERCTL/ s/USERCTL/#USERCTL/" /etc/sysconfig/network-scripts/ifcfg-vhost0
	sed -i "/^SUBCHANNELS/ s/SUBCHANNELS/#SUBCHANNELS/" /etc/sysconfig/network-scripts/ifcfg-vhost0
	
else
	[[ -f $TOP_DIR/nova_compute/ifcfg-eth0 ]] && /bin/cp -p $TOP_DIR/nova_compute/ifcfg-eth0 /etc/sysconfig/network-scripts/ifcfg-eth0
fi
[[ -f /etc/contrail/ifcfg-${this_interface} ]] && mv /etc/contrail/ifcfg-${this_interface} /etc/sysconfig/network-scripts
[[ -f keystone_grants.enc ]] && rm -f keystone_grants.enc
[[ -f .keystone_grants ]] && rm -f .keystone_grants
echo "******  Compute Node installation is now completed! *******"
