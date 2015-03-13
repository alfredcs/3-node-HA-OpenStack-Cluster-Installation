import string

template = string.Template("""
MYSQL_HOST=$__mysql_host__
MYSQL_WSREP_NODES=($__mysql_wsrep_nodes__)
""")
