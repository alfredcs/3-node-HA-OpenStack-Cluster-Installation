import string

template = string.Template("""
#!/bin/sh

# chkconfig: 2345 99 01
# description: Juniper Network Virtualization API

$__contrail_supervisorctl_lines__

#supervisorctl -s http://localhost:9004 ${1} `basename ${0}`
""")
