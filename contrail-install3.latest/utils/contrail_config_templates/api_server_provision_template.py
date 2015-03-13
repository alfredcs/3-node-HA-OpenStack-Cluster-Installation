import string

template = string.Template("""
[DEFAULTS]
prov_data_file=$__contrail_prov_data_file__
api_server_ip=$__contrail_cfgm_ip__
api_server_port=$__contrail_cfgm_port__
""")
