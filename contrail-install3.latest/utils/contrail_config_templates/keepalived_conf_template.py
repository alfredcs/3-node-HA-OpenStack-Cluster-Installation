
import string

template = string.Template("""
vrrp_script chk_haproxy_$__vip_str__ {
        script "killall -0 haproxy" # verify if pid exists
        interval 1
        timeout $__timeout__
        rise $__rise__
        fall $__fall__
}

vrrp_instance $__vip_str__ {
        interface $__device__
        state $__state__
        preempt_delay $__preempt_delay__
        garp_master_delay $__delay__
        garp_master_repeat $__garp_master_repeat__
        garp_master_refresh $__garp_master_refresh__
        advert_int 1
        virtual_router_id $__router_id__
        priority  $__priority__
        virtual_ipaddress {
                $__virtual_ip__/$__virtual_ip_mask__ dev $__device__
        }
        track_script  {
                chk_haproxy_$__vip_str__
        }
}
""")
