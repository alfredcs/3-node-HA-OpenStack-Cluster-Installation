import string

template = string.Template("""
disable_service n-net
enable_service q-svc
enable_service n-novnc
enable_service quantum
LIBVIRT_FIREWALL_DRIVER=nova.virt.firewall.NoopFirewallDriver
Q_PLUGIN=contrail
NOVA_USE_QUANTUM_API=v2
MYSQL_PASSWORD=$__contrail_mysql_password__
RABBIT_PASSWORD=$__contrail_rabbit_password__
SERVICE_TOKEN=$__contrail_service_token__
SERVICE_PASSWORD=$__contrail_service_password__
ADMIN_PASSWORD=$__contrail_admin_password__
HOST_IP=$__contrail_compute_ip__
MULTI_HOST=1
LOGFILE=/opt/stack/logs/stack.sh.log
MYSQL_HOST=$__contrail_controller_ip__
RABBIT_HOST=$__contrail_controller_ip__
KEYSTONE_SERVICE_HOST=$__contrail_controller_ip__
Q_HOST=$__contrail_controller_ip__
GLANCE_HOSTPORT=$__contrail_controller_ip__:9292
ENABLED_SERVICES=n-cpu,n-api,n-vol,q-agt

# To use with python-<project> clients:
# export OS_USERNAME=admin
# export OS_PASSWORD=contrail123
# export OS_TENANT_NAME=admin
# export OS_AUTH_URL="http://localhost:5000/v2.0"
""")
