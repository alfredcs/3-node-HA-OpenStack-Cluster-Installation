# default: on
# description: Check Contrail Neutron service from Haproxy to ensure layer 7 health
service check_neutron
{
        socket_type             = stream
        port                    = 60122
        protocol                = tcp
        wait                    = no
        user                    = root
        server                  = /usr/local/bin/check_neutron.py
        server_args             = -v
        disable                 = no
        per_source              = UNLIMITED
        cps                     = 100 2
        flags                   = REUSE
        only_from               = 0.0.0.0/0
        log_on_failure          += USERID
}
