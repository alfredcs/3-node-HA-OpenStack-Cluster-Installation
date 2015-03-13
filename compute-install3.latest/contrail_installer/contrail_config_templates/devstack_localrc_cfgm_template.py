import string

template = string.Template("""
disable_service n-net
enable_service q-svc
enable_service quantum
LIBVIRT_FIREWALL_DRIVER=nova.virt.firewall.NoopFirewallDriver
Q_PLUGIN=contrail
NOVA_USE_QUANTUM_API=v2
MYSQL_PASSWORD=$__contrail_mysql_password__
RABBIT_PASSWORD=$__contrail_rabbit_password__
SERVICE_TOKEN=$__contrail_service_token__
SERVICE_PASSWORD=$__contrail_service_password__
ADMIN_PASSWORD=$__contrail_admin_password__

# To use with python-<project> clients:
# export OS_USERNAME=admin
# export OS_PASSWORD=contrail123
# export OS_TENANT_NAME=admin
# export OS_AUTH_URL="http://localhost:5000/v2.0"
""")
