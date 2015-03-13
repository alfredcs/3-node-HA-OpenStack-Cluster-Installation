#!/bin/bash
set -x
######
# Install glussterfs on OpensStack controllers
######
function usage() {
cat <<EOF
usage: $0 options

This script will install glusterfs on a 2-node cluster

Example:
        glusterfs_install.sh -c gluster_vip -r peer_hostname_or_ip [-m mount_pount] [-b brick_name] [-v volume_name] [-d device_name] ......
controller  

OPTIONS:
  -h -- Help Show this message
  -c -- VIP of the glusterfs service
  -m -- Mount point name for glusterfs
  -b -- Glusterfs brick name
  -v -- Glusterfs volume name  
  -d -- Storage physical device name  i.e. "vda"
  -p -- Storage partition index i.e. 2
  -r -- Gluster peer's hostname or IP address
  -s -- File System type i.e. ext4 or xfs

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

[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
peer_hostname_or_ip="";glusterfs_vip="";file_system="ext4";brick_name="brick1";mount_point="/data";volume_name="gvol01";device_name="vda";partition_index="2"
while getopts "hc:d:m:b:v:p:r:s:" OPTION; do
case "$OPTION" in
d)
        device_name="$OPTARG"
        ;;
c)
	glusterfs_vip="$OPTARG"
	;;
b)
        brick_name="$OPTARG"
        ;;
m)
        mount_point="$OPTARG"
        ;;
v)
        volume_name="$OPTARG"
        ;;
p)
        parition_index="$OPTARG"
        ;;
r)
	peer_hostname_or_ip="$OPTARG"
	;;
s)
        file_system="$OPTARG"
        ;;
h)
	usage
	exit 0
	;;
:)
        usage
	exit 1
        ;;
esac
done
[[ -z ${peer_hostname_or_ip} || -z ${glusterfs_vip} ]] && { usage; exit 1; }

service glusterd stop
[[ `rpm -qa | grep glusterfs-server |wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa | grep glusterfs-server`
yum -y install --disablerepo=* --enablerepo=havana_install_repo110 glusterfs-server glusterfs-geo-replication
[[ $? -ne 0 ]] && { echo "Install glusterfs failed!"; exit 1; }
[[ `rpm -qa | grep keepalived |wc -l` -lt 1 ]] && yum -y install keepalived
chkconfig glusterfsd on
chkconfig keepalived on
service glusterd restart

umount -f ${mount_point}; [[ -d ${mount_point} ]] && rm -rf ${mount_point}
[[ `grep ${device_name}${parition_index} /etc/fstab|wc -l` -lt 1 ]] && echo "/dev/${device_name}${partition_index}  ${mount_point}  ext4    defaults    0 0" >> /etc/fstab
if [[ ! -e /dev/${device_name}${partition_index} && -e /dev/$device_name ]]; then
        (echo n; echo p;echo ${partition_index}; echo; echo +50G;echo w;echo q)| fdisk /dev/${device_name}
        partx -v -a /dev/${device_name}
        mkfs -t ${file_system} /dev/${device_name}${partition_index}
fi
[[ ! -e ${mount_point}/lost+found ]] && { mkdir -p  ${mount_point}; mount ${mount_point}; }
[[ $? -ne 0 ]] && { echo "Mount failed!"; exit 1; }
[[ ! -d ${mount_point}/${brick_name}/${volume_name} ]] && mkdir -p ${mount_point}/${brick_name}/${volume_name}
[[ -f ./keepalived/keepalived.conf.controller ]] && /bin/cp -pf ./keepalived/keepalived.conf.controller /etc/keepalived/keepalived.conf
sed -i "s/this_service/glusterd/g" /etc/keepalived/keepalived.conf
sed -i "s/this_vip/${glusterfs_vip}/g" /etc/keepalived/keepalived.conf
sed -i "s/vrrp_state/MASTER/g" /etc/keepalived/keepalived.conf
[[ -d /proc/net/bonding ]] && this_interface=`ls /proc/net/bonding|head -1`
for that_interface in `ls /sys/class/net|egrep -v 'virbr|lo'`; do [[ `cat /sys/class/net/${that_interface}/carrier` -eq 1 ]] &&  break; done
this_interface=${this_interface:-${that_interface}}
sed -i "s/this_interface/${this_interface}/g" /etc/keepalived/keepalived.conf
domain_name=`echo $HOSTNAME|cut -d\. -f2,3,4,5`
sed -i "s/this_domain/${domain_name}/g" /etc/keepalived/keepalived.conf
this_netmask=`ifconfig ${this_interface}| grep -i MASK| awk '{print $4}'| cut -d: -f2`
sed -i "s/this_cidr/$(mask2cidr ${this_netmask})/g" /etc/keepalived/keepalived.conf
this_priority=`grep $HOSTNAME /etc/hosts| grep -v ^#|head -1|awk '{print $1}'|cut -d\. -f4`
sed -i "s/this_priority/${this_priority}/g" /etc/keepalived/keepalived.conf
sed -i "s/this_router/233/g" /etc/keepalived/keepalived.conf
service keepalived restart

[[ -d ${mount_point}/${brick_name}/${volume_name} ]] && gluster volume create ${volume_name} replica 2 `grep $HOSTNAME /etc/hosts| grep -v ^#|head -1|awk '{print $1}'`:${mount_point}/${brick_name}/${volume_name} `grep ${peer_hostname_or_ip} /etc/hosts| grep -v ^#|head -1|awk '{print $1}'`:${mount_point}/${brick_name}/${volume_name}
gluster volume start ${volume_name}
