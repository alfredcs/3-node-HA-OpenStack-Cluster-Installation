import string

template = string.Template("""
[APISERVER]
api_server_ip = $__contrail_api_server_ip__
api_server_port = $__contrail_api_server_port__
multi_tenancy = $__contrail_multi_tenancy__
contrail_extensions = ipam:neutron_plugin_contrail.plugins.opencontrail.contrail_plugin_ipam.NeutronPluginContrailIpam,policy:neutron_plugin_contrail.plugins.opencontrail.contrail_plugin_policy.NeutronPluginContrailPolicy,route-table:neutron_plugin_contrail.plugins.opencontrail.contrail_plugin_vpc.NeutronPluginContrailVpc,contrail:None

[KEYSTONE]
;auth_url = $__contrail_ks_auth_protocol__://$__contrail_keystone_ip__:$__contrail_ks_auth_port__/v2.0
;admin_token = $__contrail_admin_token__
admin_user=$__contrail_admin_user__
admin_password=$__contrail_admin_password__
admin_tenant_name=$__contrail_admin_tenant_name__
""")
