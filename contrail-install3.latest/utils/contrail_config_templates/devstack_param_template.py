import string

template = string.Template("""
# To use with python-<project> clients:
export OS_USERNAME=$__contrail_os_username__
export OS_PASSWORD=$__contrail_os_password__
export OS_TENANT_NAME=$__contrail_devstack_os_tenant_name__
export OS_AUTH_URL=$__contrail_os_auth_url__
""")
