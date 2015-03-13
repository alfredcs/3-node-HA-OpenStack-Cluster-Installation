# default: on
# description: Check OpenStack Glance service from Haproxy to ensure layer 7 health
service check_glance
{
	socket_type		= stream
	port            	= 60111
	protocol		= tcp
	wait			= no
	user			= root
	server			= /usr/local/bin/check_glance.py
	server_args		= 
	disable			= no
	per_source		= UNLIMITED
	cps			= 100 2
	flags			= REUSE
	only_from		= 0.0.0.0/0
	log_on_failure  	+= USERID
}
