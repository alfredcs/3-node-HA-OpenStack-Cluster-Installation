#!/bin/bash
set -x
function usage() {
cat <<EOF
usage: $0 options

This script will Horizon on a Openstack controller

Example:
        ha_install.sh [-L] -v openstack_controller_vip  -F first_openstack_controller -S second_openstack_controller -T  third_openstack_controller

OPTIONS:
  -h -- Help Show this message
  -F -- The first contrail controller's IP address
  -L -- SSL for Keystone
  -S -- The second contrail controller's IP addressd
  -T -- The third contrail controller's IP addressd
  -V -- Verbose Verbose output
  -v -- VIP of the openstack controller

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

FIRST_CONTROLLER=""
HTTP_CMD=http
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
while getopts "hF:LS:T:v:VD" OPTION; do
case "$OPTION" in
h)
        usage
        exit 0
        ;;
F)
        first_openstack_controller="$OPTARG"
        ;;
L)
	HTTP_CMD="https"
	;;
S)
        second_openstack_controller="$OPTARG"
        ;;
T)
        third_openstack_controller="$OPTARG"
        ;;
v)
        this_vip="$OPTARG"
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

this_ip=`egrep $HOSTNAME /etc/hosts|grep -v ^#|awk '{print $1}'`
this_vip=${this_vip:-"${this_ip}"}
[[ -d /proc/net/bonding ]] && this_interface=`ls /proc/net/bonding`
for that_interface in `ls /sys/class/net|egrep -v 'virbr|lo'`; do [[ `cat /sys/class/net/${that_interface}/carrier` -eq 1 ]] &&  break; done
this_interface=${this_interface:-${that_interface}}
service haproxy stop 
service keepalived  stop 
[[ `rpm -qa | egrep 'keepalived|haproxy'|wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa|egrep 'haproxy|keepalived'`
yum -y install --disablerepo=* --enablerepo=havana_install_repo110 keepalived haproxy xinetd
[[ $? -ne 0 ]] &&  { echo "HA installation failed!"; exit 1; }
[[ -f keepalived/keepalived.conf.controller ]] && /bin/cp -fp keepalived/keepalived.conf.controller /etc/keepalived/keepalived.conf
[[ ! -d /etc/haproxy ]] && mkdir -p /etc/haproxy
[[ `grep haproxy /etc/passwd | grep -v grep |wc -l` -lt 1 ]] && adduser haproxy
[[ ! -d /var/lib/haproxy ]] && { mkdir -p /var/lib/haproxy; chown -R haproxy:haprox /var/lib/haproxy/; }
[[ ! -d /etc/keystone/ssl/certs ]] && { mkdir -p /etc/keystone/ssl/certs; chown keystone:keystone /etc/keystone/ssl/certs; }
[[ -f ./keystone/server01.pem ]] && /bin/cp -pf ./keystone/server01.pem /etc/keystone/ssl/certs/server01.pem
[[ -f haproxy/haproxy.cfg.controller && ${HTTP_CMD} == "http"  ]] && /bin/cp -fp haproxy/haproxy.cfg.controller /etc/haproxy/haproxy.cfg
[[ -f haproxy/haproxy_ssl.cfg.controller && ${HTTP_CMD} == "https"  ]] && /bin/cp -fp haproxy/haproxy_ssl.cfg.controller /etc/haproxy/haproxy.cfg
this_domain=`echo $HOSTNAME|cut -d\. -f2,3,4,5`
this_domain=${this_domain:-"default.domain"}
for conf_file in /etc/keepalived/keepalived.conf  /etc/haproxy/haproxy.cfg
do
	sed -i "s/this_vip/${this_vip}/g" ${conf_file}
	sed -i "s/first_openstack_controller/${first_openstack_controller}/g" ${conf_file}
	sed -i "s/second_openstack_controller/${second_openstack_controller}/g" ${conf_file}
	sed -i "s/third_openstack_controller/${third_openstack_controller}/g" ${conf_file}
	this_router=`echo ${this_vip} |cut -d\. -f4`
	this_priority=`echo ${this_ip} |cut -d\. -f4`
	this_netmask=`ifconfig ${this_interface}| grep -i MASK| awk '{print $4}'| cut -d: -f2`
	if [[ ${first_openstack_controller} == ${this_ip} ]]; then
		let "this_priority=255"
		sed -i "s/vrrp_state/MASTER/g" ${conf_file}
	else
		sed -i "s/vrrp_state/BACKUP/g" ${conf_file}
	fi
	sed -i "s/this_router/${this_router}/g" ${conf_file}
	sed -i "s/this_service/haproxy/g" ${conf_file}
	sed -i "s/this_domain/${this_domain}/g" ${conf_file}
	sed -i "s/this_priority/${this_priority}/g" ${conf_file}
	sed -i "s/this_cidr/$(mask2cidr ${this_netmask})/g" ${conf_file}
	sed -i "s/this_interface/${this_interface}/g" ${conf_file}
	if [[ ${HTTP_CMD} == "https" ]]; then
		sed -i "/mode/ s/KEYSTONE_LB_MODE/tcp/g" ${conf_file}
		SERVER_SSL_PEM="\/etc\/keystone\/ssl\/certs\/server01.pem"
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
service haproxy restart
service keepalived restart
