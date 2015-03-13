import string

template = string.Template("""
VIP="$__internal_vip__"
DIPS=($__haproxy_dips__)
DIPS_SIZE=${#DIPS[@]}
""")
