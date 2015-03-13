# default: on
# description: Check OpenStack Nova API service from Haproxy to ensure layer 7 health
service check_nova_api
{
	socket_type		= stream
	port            	= 60112
	protocol		= tcp
	wait			= no
	user			= root
	server			= /usr/local/bin/check_nova_api.py
	server_args		= 
	disable			= no
	per_source		= UNLIMITED
	cps			= 100 2
	flags			= REUSE
	only_from		= 0.0.0.0/0
	log_on_failure  	+= USERID
}
