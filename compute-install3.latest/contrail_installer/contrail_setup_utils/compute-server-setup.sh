#!/usr/bin/env bash

if [ -f /etc/redhat-release ]; then
   is_redhat=1
   is_ubuntu=0
   nova_compute_ver=`rpm -q --qf  "%{VERSION}\n" openstack-nova-compute`
   if [ "$nova_compute_ver" == "2013.1" ]; then
   	OS_NET=quantum
   	TENANT_NAME=quantum_admin_tenant_name
   	ADMIN_USER=quantum_admin_username
   	ADMIN_PASSWD=quantum_admin_password
   	ADMIN_AUTH_URL=quantum_admin_auth_url
   	OS_URL=quantum_url
   	OS_URL_TIMEOUT=quantum_url_timeout
   else
   	OS_NET=neutron
   	TENANT_NAME=neutron_admin_tenant_name
   	ADMIN_USER=neutron_admin_username
   	ADMIN_PASSWD=neutron_admin_password
   	ADMIN_AUTH_URL=neutron_admin_auth_url
   	OS_URL=neutron_url
   	OS_URL_TIMEOUT=neutron_url_timeout
   fi
fi

if [ -f /etc/lsb-release ] && egrep -q 'DISTRIB_ID.*Ubuntu' /etc/lsb-release; then
   is_ubuntu=1
   is_redhat=0
   nova_compute_version=`dpkg -l | grep 'ii' | grep nova-compute | grep -v vif | grep -v nova-compute-kvm | awk '{print $3}'`
   echo $nova_compute_version
   if [ "$nova_compute_version" == "2:2013.1.3-0ubuntu1" ]; then
   	OS_NET=quantum
   	TENANT_NAME=quantum_admin_tenant_name
   	ADMIN_USER=quantum_admin_username
   	ADMIN_PASSWD=quantum_admin_password
   	ADMIN_AUTH_URL=quantum_admin_auth_url
   	OS_URL=quantum_url
   	OS_URL_TIMEOUT=quantum_url_timeout
   else
   	OS_NET=neutron
   	TENANT_NAME=neutron_admin_tenant_name
   	ADMIN_USER=neutron_admin_username
   	ADMIN_PASSWD=neutron_admin_password
   	ADMIN_AUTH_URL=neutron_admin_auth_url
   	OS_URL=neutron_url
   	OS_URL_TIMEOUT=neutron_url_timeout
   fi
fi

#CONTROLLER=10.1.5.12
#SERVICE_TOKEN=ded4dd496c91df8eb61b

if [ $is_ubuntu -eq 1 ] ; then
    lsmod | grep kvm
    if [ $? -ne 0 ]; then
        modprobe -a kvm
        echo "kvm" >> /etc/modules
        VENDOR=`cat /proc/cpuinfo | grep 'vendor_id' | cut -d: -f2 | awk 'NR==1'`
        if [[ "${VENDOR}" == *Intel* ]]; then
            modprobe -a kvm-intel
            echo "kvm-intel" >> /etc/modules
        else
            modprobe -a kvm-amd
            echo "kvm-amd" >> /etc/modules
        fi
    fi
fi
source /etc/contrail/ctrl-details
if [ $CONTROLLER != $COMPUTE ] ; then
    openstack-config --del /etc/nova/nova.conf DEFAULT sql_connection
    openstack-config --set /etc/nova/nova.conf DEFAULT auth_strategy keystone
    openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_nonblocking True
    openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_inject_partition -1
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_host $AMQP_SERVER
    openstack-config --set /etc/nova/nova.conf DEFAULT glance_host $CONTROLLER
    openstack-config --set /etc/nova/nova.conf DEFAULT $TENANT_NAME service
    openstack-config --set /etc/nova/nova.conf DEFAULT $ADMIN_USER $OS_NET
    openstack-config --set /etc/nova/nova.conf DEFAULT $ADMIN_PASSWD $SERVICE_TOKEN
    openstack-config --set /etc/nova/nova.conf DEFAULT $ADMIN_AUTH_URL $AUTH_PROTOCOL://$CONTROLLER:35357/v2.0/
    openstack-config --set /etc/nova/nova.conf DEFAULT $OS_URL ${QUANTUM_PROTOCOL}://$QUANTUM:9696/
    openstack-config --set /etc/nova/nova.conf DEFAULT $OS_URL_TIMEOUT 300
    if [ $is_ubuntu -eq 1 ] ; then
        openstack-config --set /etc/nova/nova.conf DEFAULT network_api_class nova.network.${OS_NET}v2.api.API
        openstack-config --set /etc/nova/nova.conf DEFAULT compute_driver libvirt.LibvirtDriver
    else
        if [ "$nova_compute_ver" == "2014.1.1" ]; then
            openstack-config --set /etc/nova/nova.conf DEFAULT compute_driver libvirt.LibvirtDriver
            openstack-config --set /etc/nova/nova.conf DEFAULT network_api_class nova.network.${OS_NET}v2.api.API
            openstack-config --set /etc/nova/nova.conf DEFAULT state_path /var/lib/nova
            openstack-config --set /etc/nova/nova.conf DEFAULT lock_path /var/lib/nova/tmp
            openstack-config --set /etc/nova/nova.conf DEFAULT instaces_path /var/lib/nova/instances
        fi
    fi
    openstack-config --set /etc/nova/nova.conf keystone_authtoken admin_tenant_name service
    openstack-config --set /etc/nova/nova.conf keystone_authtoken admin_user nova
    openstack-config --set /etc/nova/nova.conf keystone_authtoken admin_password $SERVICE_TOKEN
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_host $CONTROLLER
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_protocol http
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_port 35357
    openstack-config --set /etc/nova/nova.conf keystone_authtoken signing_dir /tmp/keystone-signing-nova
fi

if [ $VMWARE_IP ]; then
    openstack-config --del /etc/nova/nova.conf DEFAULT compute_driver
    openstack-config --set /etc/nova/nova.conf DEFAULT compute_driver vmwareapi.ContrailESXDriver
    if [ -f /etc/nova/nova-compute.conf ]; then
        openstack-config --del /etc/nova/nova-compute.conf DEFAULT compute_driver
        openstack-config --set /etc/nova/nova-compute.conf DEFAULT compute_driver vmwareapi.ContrailESXDriver
    fi
fi

openstack-config --set /etc/nova/nova.conf DEFAULT ec2_private_dns_show_ip False
openstack-config --set /etc/nova/nova.conf DEFAULT novncproxy_base_url http://$CONTROLLER_MGMT:5999/vnc_auto.html
openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_enabled true
openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_listen $COMPUTE
openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_proxyclient_address $COMPUTE
openstack-config --set /etc/nova/nova.conf DEFAULT security_group_api $OS_NET

openstack-config --set /etc/nova/nova.conf DEFAULT heal_instance_info_cache_interval  0
openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_cpu_mode none
openstack-config --set /etc/nova/nova.conf DEFAULT image_cache_manager_interval 0

#use contrail specific vif driver
openstack-config --set /etc/nova/nova.conf DEFAULT libvirt_vif_driver nova_contrail_vif.contrailvif.VRouterVIFDriver

# Use noopdriver for firewall
openstack-config --set /etc/nova/nova.conf DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver

if [ $VMWARE_IP ]; then
    openstack-config --set /etc/nova/nova.conf vmware host_ip $VMWARE_IP
    openstack-config --set /etc/nova/nova.conf vmware host_username $VMWARE_USERNAME
    openstack-config --set /etc/nova/nova.conf vmware host_password $VMWARE_PASSWD
    openstack-config --set /etc/nova/nova.conf vmware vmpg_vswitch $VMWARE_VMPG_VSWITCH
fi

# Openstack HA specific configs
INTERNAL_VIP=${INTERNAL_VIP:-none}
CONTRAIL_INTERNAL_VIP=${CONTRAIL_INTERNAL_VIP:-none}
if [ "$INTERNAL_VIP" != "none" ]; then
    openstack-config --set /etc/nova/nova.conf DEFAULT glance_port 9292
    openstack-config --set /etc/nova/nova.conf DEFAULT glance_num_retries 10
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_host $INTERNAL_VIP
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_port 5000
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_host $AMQP_SERVER
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_port 5673
    openstack-config --set /etc/nova/nova.conf DEFAULT $ADMIN_AUTH_URL http://$INTERNAL_VIP:5000/v2.0/
    openstack-config --set /etc/nova/nova.conf DEFAULT $OS_URL http://$CONTRAIL_INTERNAL_VIP:9696/
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_retry_interval 1
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_retry_backoff 2
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_max_retries 0
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_ha_queues True
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_cast_timeout 30
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_conn_pool_size 40
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_response_timeout 60
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_thread_pool_size 70
    openstack-config --set /etc/nova/nova.conf DEFAULT report_interval 5
    openstack-config --set /etc/nova/nova.conf DEFAULT novncproxy_port 6080
    openstack-config --set /etc/nova/nova.conf DEFAULT vnc_port 5900
    openstack-config --set /etc/nova/nova.conf DEFAULT vnc_port_total 100
    openstack-config --set /etc/nova/nova.conf DEFAULT novncproxy_base_url http://$EXTERNAL_VIP:6080/vnc_auto.html
    openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_listen $SELF_MGMT_IP
    openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_proxyclient_address $SELF_MGMT_IP
    openstack-config --set /etc/nova/nova.conf DEFAULT resume_guests_state_on_host_boot True
elif [ "$CONTRAIL_INTERNAL_VIP" != "none" ]; then
    openstack-config --set /etc/nova/nova.conf DEFAULT glance_port 9292
    openstack-config --set /etc/nova/nova.conf DEFAULT glance_num_retries 10
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_host $CONTROLLER
    openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_port 5000
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_host $AMQP_SERVER
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_port 5672
    openstack-config --set /etc/nova/nova.conf DEFAULT $ADMIN_AUTH_URL http://$CONTROLLER:5000/v2.0/
    openstack-config --set /etc/nova/nova.conf DEFAULT $OS_URL http://$CONTRAIL_INTERNAL_VIP:9696/
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_retry_interval 1
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_retry_backoff 2
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_max_retries 0
    openstack-config --set /etc/nova/nova.conf DEFAULT rabbit_ha_queues True
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_cast_timeout 30
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_conn_pool_size 40
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_response_timeout 60
    openstack-config --set /etc/nova/nova.conf DEFAULT rpc_thread_pool_size 70
    openstack-config --set /etc/nova/nova.conf DEFAULT report_interval 5
    openstack-config --set /etc/nova/nova.conf DEFAULT novncproxy_port 6080
    openstack-config --set /etc/nova/nova.conf DEFAULT vnc_port 5900
    openstack-config --set /etc/nova/nova.conf DEFAULT vnc_port_total 100
    openstack-config --set /etc/nova/nova.conf DEFAULT novncproxy_base_url http://$CONTROLLER_MGMT:6080/vnc_auto.html
    openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_listen $SELF_MGMT_IP
    openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_proxyclient_address $SELF_MGMT_IP
    openstack-config --set /etc/nova/nova.conf DEFAULT resume_guests_state_on_host_boot True
fi

for svc in openstack-nova-compute supervisor-vrouter; do
    chkconfig $svc on
done

#for svc in openstack-nova-compute; do
#    service $svc restart
#done
