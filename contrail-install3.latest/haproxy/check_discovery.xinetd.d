# default: on
# description: Check Contrail Discovery service from Haproxy to ensure layer 7 health
service check_discovery
{
        socket_type             = stream
        port                    = 60121
        protocol                = tcp
        wait                    = no
        user                    = root
        server                  = /usr/local/bin/check_discovery.py
        server_args             = -v
        disable                 = no
        per_source              = UNLIMITED
        cps                     = 100 2
        flags                   = REUSE
        only_from               = 0.0.0.0/0
        log_on_failure          += USERID
}
