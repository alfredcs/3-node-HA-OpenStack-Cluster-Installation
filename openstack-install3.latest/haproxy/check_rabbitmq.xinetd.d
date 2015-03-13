# default: on
# description: Check Rabbitmq service from Haproxy to ensure layer 7 health
service check_rabbitmq
{
	socket_type		= stream
	port            	= 60113
	protocol		= tcp
	wait			= no
	user			= root
	server			= /usr/local/bin/check_rabbitmq.py
	server_args		= 
	disable			= no
	per_source		= UNLIMITED
	cps			= 100 2
	flags			= REUSE
	only_from		= 0.0.0.0/0
	log_on_failure  	+= USERID
}
