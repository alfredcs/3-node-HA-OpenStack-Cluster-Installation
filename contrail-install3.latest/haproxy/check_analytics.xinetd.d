# default: on
# description: Check Contrail Analytics service from Haproxy to ensure layer 7 health
service check_analytics
{
        socket_type             = stream
        port                    = 60123
        protocol                = tcp
        wait                    = no
        user                    = root
        server                  = /usr/local/bin/check_analytics.py
        server_args             = -v
        disable                 = no
        per_source              = UNLIMITED
        cps                     = 100 2
        flags                   = REUSE
        only_from               = 0.0.0.0/0
        log_on_failure          += USERID
}
