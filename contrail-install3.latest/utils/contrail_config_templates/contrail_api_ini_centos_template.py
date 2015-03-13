import string

template = string.Template("""
[program:contrail-api]
command=/usr/bin/contrail-api --conf_file /etc/contrail/contrail-api.conf --listen_port $__contrail_api_port_base__%(process_num)01d --worker_id %(process_num)s
;command=/bin/bash -c "source /opt/contrail/api-venv/bin/activate && PYTHONPATH=/usr/lib/python2.6/site-packages exec python /opt/contrail/api-venv/lib/python2.7/site-packages/vnc_cfg_api_server/vnc_cfg_api_server.py --conf_file /etc/contrail/contrail-api.conf --listen_port $__contrail_api_port_base__%(process_num)01d --worker_id %(process_num)s"
numprocs=$__contrail_api_nworkers__
process_name=%(process_num)s
redirect_stderr=true
stdout_logfile= /var/log/contrail/contrail-api-%(process_num)s.log
stderr_logfile=/dev/null
priority=440
autostart=true
killasgroup=true
stopsignal=KILL
exitcodes=0
""")
