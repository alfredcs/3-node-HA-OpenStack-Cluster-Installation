The OpenStack installation package contains codes to install and 
configure a 3-node OpenStack control cluster based on the architecture
detailed out in the SDN POC page.  The package will install Keystone,
Glance and Nova components along with Neutron configuration on a 3-node
cluster based on Havana code release. Additional components such as
RabbitMQ, Keepalived, Haproxy and MySQL/Galera will also be installed
to support the cluster operation.

A separated glusterfs cluster is required to serve glance image
repository and other shared services. The cluster is essential for nova
instance images if to support VM migration across different hypervisor.
The glusterfs cluster is recommended to be built on a 2-node cluster
with minimum 500G storage space. A installation script
gluster_install.sh is included to standup such a cluster.

OpenStack HA Installation Steps

1. Make sure all control nodes' clock are synced and iptables rules allow needed connection requests
2. Make sure all Openstack controller nodes have needed entries in /etc/hosts, including VIPs
3. Make sure appropriate repos are specified in /etc/yum.repos.d4
4. Yum install openstack-install3 package
5. Identify an existing glusterfs cluster or configure a new one with following script
    Example: gluster_install.sh -c glusterfs_vip [-m mount_point] [-b brick_name] [-v volume_name] [-d device_name] ......
6. Install OpenStack components on the first OpenStack controller node
    i.e. openstack_install3.sh [-L] -v openstack_controller_vip   -c contrail_controller_vip  -F first_openstack_controller -S second_openstack_controller -T third_openstack_controller [ -e glusterfs_vip] [-m glusterfs_volume_name]

7. Repeat step 4 on the second OpenStack controller node
8. Repeat step 4 on the third OpenStack controller node
9. If needed, restart following services:

service rabbitmq-server start|stop|restart
service mysql start|stop|restart
service keepalived start|stop|restart
service haproxy start|stop|restart
service openstack-keystone start|stop|restart
service openstack-glance-api start|stop|restart
service openstack-glance-registry start|stop|restart
service openstack-nova-api start|stop|restart
service openstack-nova-cert start|stop|restart
service openstack-nova-conductor start|stop|restart
service openstack-nova-consoleauth start|stop|restart
service openstack-nova-novncproxy start|stop|restart
service openstack-nova-scheduler start|stop|restart
service httpd start|stop|restart

That's about it for OpenStack !

--------------------------------------------

The SDN installation package contains codes to install, configure and
provision Contrail services on a 3-node cluster based on V1.1 release.
The package will install Contrail Database, UI, Control, Analytics and
Config components on the 3-code cluster with multi-tenancy enabled.
Contrail replaces Neutron by providing SDn solution to the native NaaS
in OpenStack. By integrating with OpenStack, Contrail services interact
with the already installed OpenStack cluster for credential and message
queue services while OpenStack call Contrail API for network services.
All interactions are through RESTful API calls.

Contrail HA Installation Steps

1. Make sure all control nodes' clock are synced with OpenStack control nodes and iptables rules allow needed connection requests
2. Make sure all Openstack controller nodes have needed entries in /etc/hosts, including VIPs
3. Make sure appropriate repos are specified in /etc/yum.repos.d
4. Yum install sdn-install3 package
5. Install Contrail components on the first Contrail controller node
    i.e. ./contrail_neutron_install3.sh [-L] -o openstack_controller_vip  -F first_contrail_controller -S second_contrail_controller -T third_contrail_controller

6. Repeat step 4 on the second Contrail controller node
7. Repeat step 4 on the third Contrail controller node
8. Restart all services list below all on the 3 Contrail controller nodes

    service keepalived restart
    service haproxy restart
    service zookeeper restart
    service supervisor-analytics restart
    service supervisor-config restart
    service supervisor-control restart
    service supervisor-webui restart
    service supervisord-contrail-database restart
    service neutron-server restart

Now you have NaaS with SDN. Almost there......

------------------------------------------------

The compute installation package install, configure and provision Nova
compute and vrouter services on a compute node. It fetch credentials
from OpenStack controller and insert configuration parameters. This
version on compute install supports two network interface allocation
model for all-in-one and separation of admin and data services with or
without NIC bonding.

Compute Installation Steps

1. Make sure all compute node's clock is synced with OpenStack/Contrail control nodes
2. Make sure all Openstack controller nodes have needed entries in /etc/hosts, including VIPs
3. Make sure appropriate repos and specified in /etc/yum.repos.d
4. make sure the OS kernel matches the prerequisite
5. Yum install compute-install3 package
6. Install Compute components on the designate compute node
    i.e. compute_install3.sh [-L] -o openstack_controller_vip

7. Reboot the compute node

The cluster should be up, Have fun!
