import sys
import os
import argparse
import ConfigParser
import xml.etree.ElementTree as ET

class AgentXmlParams():
    def __init__(self):
        self.xmpp_server1=""
        self.xmpp_server2=""
        self.dns_server1=""
        self.dns_server2=""
        self.flow_timeout=""
        self.tunnel_type=""
        self.discovery_ip=""
        self.hypervisor_type=""
        self.xen_ll_ip=""
        self.xen_ll_interface=""
        self.vmware_interface=""
        self.max_control_nodes=""
        self.max_system_flows=""
        self.max_vm_flows=""
        self.metadata_secret=""
        self.control_network_ip=""
        self.vhost_name=""
        self.vhost_ip=""
        self.vhost_gw=""
        self.physical_interface=""
        self.gateway_idx=0
        self.gateway_str=""
    #end __init__

class Xml2Ini():
    def __init__(self, args_str = None):
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python xml2ini.py --source_file filename1 --target_file filename2 
                              --overwrite_target_file
        '''
        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False,
                                              formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        # Override with CLI options
        # Don't surpress add_help here so it will handle -h
        parser = argparse.ArgumentParser(
            # Inherit options from config_parser
            parents=[conf_parser],
            # print script description with -h/--help
            description=__doc__,
            # Don't mess with format of description
            formatter_class=argparse.RawDescriptionHelpFormatter,
            )
        parser.add_argument("--source_file", default="/etc/contrail/agent.conf", help = "Agent conf file name having config in XML format  (default: %(default)s)")
        parser.add_argument("--target_file", default="/etc/contrail/contrail-vrouter-agent.conf", help = "Target Agent conf file name which will have INI config  (default: %(default)s)")
        parser.add_argument("--overwrite_target_file", help = "Overwrite target file if it is already present", action='store_true')
        self._args = parser.parse_args(remaining_argv)

    #end __parse_args__

    def process_vhost(self, item, obj):
        for child_item in item:
            if child_item.tag == "name":
                obj.vhost_name = child_item.text
            elif child_item.tag == "ip-address":
                obj.vhost_ip = child_item.text
            elif child_item.tag == "gateway":
                obj.vhost_gw = child_item.text
    #end process_vhost

    def process_eth_port(self, item, obj):
        for child_item in item:
            if child_item.tag == "name":
                obj.physical_interface=child_item.text
    #end process_eth_port

    def process_discovery(self, item, obj):
        for child_item in item:
            if child_item.tag == "ip-address":
                obj.discovery_ip = child_item.text
            elif child_item.tag == "control-instances":
                obj.max_control_nodes = child_item.text
    #end process_discovery

    def process_control(self, item, obj):
        for child_item in item:
            if child_item.tag == "ip-address":
                obj.control_network_ip = child_item.text
    #end process_control

    def process_hypervisor(self, item, obj):
        self.hypervisor_type = item.attrib["mode"]
        for child_item in item:
            if child_item.tag == "xen-ll-port":
                self.xen_ll_interface = child_item.text
            elif child_item.tag == "xen-ll-ip-address":
                self.en_ll_ip = child_item.text
            if child_item.tag == "port":
                self.vmware_interface = child_item.text
    #end process_hypervisor

    def process_metadata(self, item, obj):
        for child_item in item:
            if child_item.tag == "shared-secret":
                obj.metadata_secret = child_item.text
    #end process_metadata

    def process_flow_cache(self, item, obj):
        for child_item in item:
            if child_item.tag == "timeout":
                obj.flow_timeout = child_item.text
    #end process_flow_cache

    def process_xmpp_server(self, item, obj):
        for child_item in item:
            if child_item.tag == "ip-address":
                if not obj.xmpp_server1:
                    obj.xmpp_server1 = child_item.text
                else:
                    obj.xmpp_server2 = child_item.text
    #end process_xmpp_server

    def process_dns_server(self, item, obj):
        for child_item in item:
            if child_item.tag == "ip-address":
                if not obj.dns_server1:
                    obj.dns_server1 = child_item.text
                else:
                    obj.dns_server2 = child_item.text
    #end process_dns_server

    def process_gateway(self, item, obj):
        subnet_list = []
        route_list = []
        obj.gateway_str += "[GATEWAY-%d]\n" %(obj.gateway_idx)
        obj.gateway_str += "# Name of the routing_instance for which the gateway is being configured\n"
        ri_name = item.attrib["virtual-network"]
        if not ri_name:
            ri_name = item.attrib["routing-instance"]
        obj.gateway_str += "routing_instance=%s\n\n" %(ri_name)
        for child_item in item:
            if child_item.tag == "interface":
                obj.gateway_str += "# Gateway interface name\n"
                obj.gateway_str += "interface=%s\n\n" %(child_item.text)
            elif child_item.tag == "subnet":
                subnet_list.append(child_item.text)
            elif child_item.tag == "":
                route_list.append(child_item.text)
        obj.gateway_str += "# Virtual network ip blocks for which gateway service is required. Each IP\n"
        obj.gateway_str += "# block is represented as ip/prefix. Multiple IP blocks are represented by\n"
        obj.gateway_str += "# separating each with a space\n"
        if subnet_list:
            obj.gateway_str += "ip_blocks="
            for subnet in subnet_list:
                obj.gateway_str += "%s " %(subnet)
            obj.gateway_str += "\n\n"
        else:
            obj.gateway_str += "# ip_blocks=ip1/prefix1 ip2/prefix2\n\n"
        obj.gateway_str += "# Routes to be exported in routing_instance. Each route is represented as\n"
        obj.gateway_str += "# ip/prefix. Multiple routes are represented by separating each with a space\n"
        if route_list:
            obj.gateway_str += "routes="
            for route in route_list:
                obj.gateway_str += "%s " %(route)
            route_str += "\n\n"
        else:
            obj.gateway_str += "# routes=ip1/prefix1 ip2/prefix2\n\n"
        obj.gateway_idx = obj.gateway_idx + 1
    #end process_gateway

    def convert(self):
        if not os.path.isfile(self._args.source_file):
            print 'Source file %s does not exist' %(self._args.source_file)
            return
        if os.path.isfile(self._args.target_file):
            if not self._args.overwrite_target_file:
                print 'Target file %s already exists' %(self._args.target_file)
                return
        agent_tree = ET.parse(self._args.source_file)
        agent_root = agent_tree.getroot()
        agent_elem = agent_root.find('agent')
        obj = AgentXmlParams()
        for item in agent_elem:
            if item.tag == "vhost":
                self.process_vhost(item, obj)
            elif item.tag == "eth-port":
                self.process_eth_port(item, obj)
            elif item.tag == "discovery-server":
                self.process_discovery(item, obj)
            elif item.tag == "control":
                self.process_control(item, obj)
            elif item.tag == "hypervisor":
                self.process_hypervisor(item, obj)
            elif item.tag == "tunnel-type":
                obj.tunnel_type = item.text
            elif item.tag == "metadata-proxy":
                self.process_metadata(item, obj)
            elif item.tag == "xmpp-server":
                self.process_xmpp_server(item, obj)
            elif item.tag == "dns-server":
                self.process_dns_server(item, obj)
            elif item.tag == "flow-cache":
                self.process_flow_cache(item, obj)
            elif item.tag == "gateway":
                self.process_gateway(item, obj)

        #Generate the agent config file in INI format.
        ini_str += "[CONTROL-NODE]\n" 
        ini_str += "# IP address to be used to connect to control-node. Maximum of 2 IP addresses\n"
        ini_str += "# (separated by a space) can be provided. If no IP is configured then the\n"
        ini_str += "# value provided by discovery service will be used. (Optional)\n"
        if obj.xmpp_server1 or obj.xmpp_server2:
            ini_str += "server=%s %s\n\n" %(obj.xmpp_server1, obj.xmpp_server2)
        else:
            ini_str += "# server=x.x.x.x y.y.y.y\n\n"

        ini_str += "[DEFAULT]\n"
        ini_str += "# Everything in this section is optional\n\n"
        #Collector configuration was not supported via conf file in 1.05 and earlier releases
        #Add only commented section for collector
        ini_str += "# IP address and port to be used to connect to collector. If these are not\n"
        ini_str += "# configured, value provided by discovery service will be used. Multiple\n"
        ini_str += "# IP:port strings separated by space can be provided\n"
        ini_str += "# collectors=127.0.0.1:8086\n\n"
        #Debug logging configuration was not supported in 1.05 and earlier releases
        #Add only commented item for debug logging config
        ini_str += "# Enable/disable debug logging. Possible values are 0 (disable) and 1 (enable)\n"
        ini_str += "# debug=0\n\n"
        ini_str += "# Aging time for flow-records in seconds\n"
        if obj.flow_timeout:
            ini_str += "flow_cache_timeout=%s\n\n" %(obj.flow_timeout)
        else:
            ini_str += "# flow_cache_timeout=0\n\n"

        #The following configuration was not supported via conf file in 1.05 and earlier releases
        #Add only commented items for these config
        ini_str += "# Hostname of compute-node. If this is not configured value from `hostname`\n"
        ini_str += "# will be taken\n"
        ini_str += "# hostname=\n\n"
        ini_str += "# Http server port for inspecting vnswad state (useful for debugging)\n"
        ini_str += "# http_server_port=8085\n\n"
        ini_str += "# Category for logging. Default value is '*'\n"
        ini_str += "# log_category=\n\n"
        ini_str += "# Local log file name\n"
        ini_str += "# log_file=/var/log/contrail/vrouter.log\n\n"
        ini_str += "# Log severity levels. Possible values are SYS_EMERG, SYS_ALERT, SYS_CRIT,\n"
        ini_str += "# SYS_ERR, SYS_WARN, SYS_NOTICE, SYS_INFO and SYS_DEBUG. Default is SYS_DEBUG\n"
        ini_str += "# log_level=SYS_DEBUG\n\n"
        ini_str += "# Enable/Disable local file logging. Possible values are 0 (disable) and 1 (enable)\n"
        ini_str += "# log_local=0\n\n"
        ini_str += "# Encapsulation type for tunnel. Possible values are MPLSoGRE, MPLSoUDP, VXLAN\n"
        if obj.tunnel_type:
            ini_str += "tunnel_type=%s\n\n" %(obj.tunnel_type)
        else:
            ini_str += "# tunnel_type=\n\n"

        ini_str += "[DISCOVERY]\n"
        ini_str += "# If COLLECTOR and/or CONTROL-NODE and/or DNS is not specified this section is\n"
        ini_str += "# mandatory. Else this section is optional\n\n"
        ini_str += "# IP address of discovery server\n"
        if obj.discovery_ip:
            ini_str += "server=%s\n\n" %(obj.discovery_ip)
        else:
            ini_str += "# server=10.204.217.52\n\n"
        ini_str += "# Number of control-nodes info to be provided by Discovery service. Possible\n"
        ini_str += "# values are 1 and 2\n"
        if obj.max_control_nodes:
            ini_str += "max_control_nodes=%s\n\n" %(obj.max_control_nodes)
        else:
            ini_str += "# max_control_nodes=1\n\n"
        ini_str += "[DNS]\n"
        ini_str += "# IP address to be used to connect to dns-node. Maximum of 2 IP addresses\n"
        ini_str += "# (separated by a space) can be provided. If no IP is configured then the\n"
        ini_str += "# value provided by discovery service will be used. (Optional)\n"
        if obj.dns_server1 or obj.dns_server2:
            ini_str += "server=%s %s\n\n" %(obj.dns_server1, obj.dns_server2)
        else:
            ini_str += "# server=x.x.x.x y.y.y.y\n\n"

        ini_str += "[HYPERVISOR]\n"
        ini_str += "# Everything in this section is optional\n\n"
        ini_str += "# Hypervisor type. Possible values are kvm, xen and vmware\n"
        if obj.hypervisor_type:
            ini_str += "# type=%s\n\n" %(obj.hypervisor_type)
        else:
            ini_str += "# type=kvm\n\n"

        ini_str += "# Link-local IP address and prefix in ip/prefix_len format (for xen)\n"
        if obj.xen_ll_ip:
            ini_str += "xen_ll_ip=%s\n\n" %(obj.xen_ll_ip)
        else:
            ini_str += "# xen_ll_ip=\n\n"

        ini_str += "# Link-local interface name when hypervisor type is Xen\n"
        if obj.xen_ll_interface:
            ini_str += "xen_ll_interface=%s\n\n" %(obj.xen_ll_interface)
        else:
            ini_str += "# xen_ll_interface=\n\n"

        ini_str += "# Physical interface name when hypervisor type is vmware\n"
        if obj.vmware_interface:
            ini_str += "vmware_physical_interface=%s\n\n" %(obj.vmware_interface)
        else:
            ini_str += "# vmware_physical_interface=\n\n"

        ini_str += "[FLOWS]\n"
        ini_str += "# Everything in this section is optional\n\n"
        ini_str += "# Maximum flows allowed per VM - given as \% of maximum system flows\n"
        ini_str += "# max_vm_flows=100\n\n"
        ini_str += "# Maximum number of link-local flows allowed across all VMs\n"
        if obj.max_system_flows:
            ini_str += "max_system_linklocal_flows=%s\n\n" %(obj.max_system_flows)
        else:
            ini_str += "# max_system_linklocal_flows=4096\n\n"
        ini_str += "# Maximum number of link-local flows allowed per VM\n"
        if obj.max_vm_flows:
            ini_str += "max_vm_linklocal_flows=%s\n\n" %(obj.max_vm_flows)
        else:
            ini_str += "# max_vm_linklocal_flows=1024\n\n"

        ini_str += "[METADATA]\n"
        ini_str += "# Shared secret for metadata proxy service. (Optional)\n"
        if obj.metadata_secret:
            ini_str += "metadata_proxy_secret=%s\n\n" %(obj.metadata_secret)
        else:
            ini_str += "# metadata_proxy_secret=contrail\n\n"

        ini_str += "[NETWORKS]\n"
        ini_str += "# control-channel IP address used by WEB-UI to connect to vnswad to fetch\n"
        ini_str += "# required information (Optional)\n"
        if obj.control_network_ip:
            ini_str += "control_network_ip=%s\n\n" %(obj.control_network_ip)
        else:
            ini_str += "# control_network_ip=\n\n"
        
        ini_str += "[VIRTUAL-HOST-INTERFACE]\n"
        ini_str += "# Everything in this section is mandatory\n\n"
        ini_str += "# name of virtual host interface\n"
        ini_str += "name=%s\n\n" %(obj.vhost_name)

        ini_str += "# IP address and prefix in ip/prefix_len format\n"
        ini_str += "ip=%s\n\n" %(obj.vhost_ip)

        ini_str += "# Gateway IP address for virtual host\n"
        ini_str += "gateway=%s\n\n" %(obj.vhost_gw)

        ini_str += "# Physical interface name to which virtual host interface maps to\n"
        ini_str += "physical_interface=%s\n\n" %(obj.physical_interface)

        ini_str += obj.gateway_str

        with open(self._args.target_file, "w") as f:
            f.write(ini_str)

    #end __convert__

    def convert_supervisor_ini(self):
        os.system("sed -i 's/command=.*/command=\/usr\/bin\/vnswad/g' /etc/contrail/supervisord_vrouter_files/contrail-vrouter.ini")
    #end __convert_supervisor_ini__

def main(args_str = None):
    obj = Xml2Ini(args_str)
    obj.convert()
    obj.convert_supervisor_ini()
#end main

if __name__ == "__main__":
    main()
