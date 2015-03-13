#!/usr/bin/python

import argparse
import ConfigParser

import os
import sys
import time
import netaddr
import subprocess
from pprint import pformat

import tempfile
from fabric.api import local, env, run
from fabric.operations import get, put
from fabric.context_managers import lcd, settings
sys.path.insert(0, os.getcwd())

class SetupNFSLivem(object):

    # Added global variables for the files.
    # Use the variables instead of the filenames directly in the script
    # to avoid typos and readability. 
    global ETC_FSTAB
    ETC_FSTAB='/etc/fstab'
    global TMP_FSTAB
    TMP_FSTAB='/tmp/fstab'
    global NOVA_INST_GLOBAL
    NOVA_INST_GLOBAL='/var/lib/nova/instances/global'

    def __init__(self, args_str = None):
        print sys.argv[1:]
        self._args = None
        if not args_str:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)
        vm_running = 0

        print self._args.storage_setup_mode
        nfs_livem_image = self._args.nfs_livem_image[0]
        nfs_livem_host = self._args.nfs_livem_host[0]
        nfs_livem_subnet = self._args.nfs_livem_subnet[0]
        nfs_livem_cidr = str (netaddr.IPNetwork('%s' %(nfs_livem_subnet)).cidr)
        if self._args.storage_setup_mode == 'setup' or \
            self._args.storage_setup_mode == 'setup_global':

            #check for vm image if already present, otherwise add it
            livemnfs=local('source /etc/contrail/openstackrc && /usr/bin/glance image-list | grep livemnfs|wc -l', capture=True, shell='/bin/bash')
            if livemnfs == '1':
                print 'NFS Live migration is already configured'
            else:
                print 'NFS Live migration is yet to be configured'
                local('source /etc/contrail/openstackrc && /usr/bin/glance image-create --name livemnfs --disk-format qcow2 --container-format ovf --file %s --is-public True' %(nfs_livem_image) , capture=True, shell='/bin/bash')
                livemnfs=local('source /etc/contrail/openstackrc && /usr/bin/glance image-list | grep livemnfs|wc -l', capture=True, shell='/bin/bash')
                if livemnfs == '1':
                    print 'image add success'
                else:
                    return

            # default vm host values
            memtotal = 16 * 1024 * 1024
            cputotal = 8
            for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                if hostname == nfs_livem_host:
                    with settings(host_string = 'root@%s' %(entries), password = entry_token):
                        memtotal = run('cat /proc/meminfo  | grep MemTotal | tr -s \' \' | cut -d " " -f 2', shell='/bin/bash')
                        cputotal = run(' cat /proc/cpuinfo  | grep processor |  wc -l', shell='/bin/bash')

            if long(memtotal) >= 32 * 1024 * 1024:
                memselect = "16384"
            else:
                memselect = "8192"

            if int(cputotal) >= 16:
                cpuselect = "8"
            else:
                cpuselect = "4"

            nova_flavor_avail=local('source /etc/contrail/openstackrc && \
                                    nova flavor-list |grep nfsvm_flavor|wc -l',
                                    capture=True, shell='/bin/bash')
            if nova_flavor_avail == '0':
                local('source /etc/contrail/openstackrc && \
                        nova flavor-create nfsvm_flavor 100 %s 20 %s'
                        %(memselect, cpuselect), shell='/bin/bash')

            #check for neutron network if already present, otherwise add it
            neutronnet=local('source /etc/contrail/openstackrc && neutron net-list | grep livemnfs|wc -l', capture=True, shell='/bin/bash')
            if neutronnet == '0':
                local('source /etc/contrail/openstackrc && neutron net-create livemnfs', shell='/bin/bash')

            #check for neutron subnet if already present, otherwise add it
            neutronsubnet=local('source /etc/contrail/openstackrc && neutron subnet-list | grep %s |wc -l' %(nfs_livem_cidr), capture=True, shell='/bin/bash')
            if neutronsubnet == '0':
                local('source /etc/contrail/openstackrc && neutron subnet-create --name livemnfs livemnfs %s' %(nfs_livem_cidr), shell='/bin/bash')
            net_id = livemnfs=local('source /etc/contrail/openstackrc && neutron net-list |grep livemnfs| awk \'{print $2}\'', capture=True, shell='/bin/bash')

            #check for vm if already running, otherwise start it
            vm_running=local('source /etc/contrail/openstackrc && nova list | grep livemnfs |grep ACTIVE |wc -l' , capture=True, shell='/bin/bash')
            if vm_running == '0':
                vm_present=local('source /etc/contrail/openstackrc && nova list | grep livemnfs |wc -l' , capture=True, shell='/bin/bash')
                if vm_present == '0':
                    local('source /etc/contrail/openstackrc && nova boot --image livemnfs --flavor 100 --availability-zone nova:%s --nic net-id=%s livemnfs --meta storage_scope=local' %(nfs_livem_host, net_id), shell='/bin/bash')
                else:
                    local('source /etc/contrail/openstackrc && nova start livemnfs', shell='/bin/bash')
                wait_loop = 10
                while True:
                    vm_running=local('source /etc/contrail/openstackrc && nova list | grep livemnfs |grep ACTIVE |wc -l' , capture=True, shell='/bin/bash')
                    if vm_running == '1':
                       break
                    wait_loop -= 1
                    if wait_loop <= 0:
                       break
                    time.sleep(10)

            #copy nova,libvirt,kvm entries
            novapassentry = ''
            libqpassentry = ''
            libdpassentry = ''
            libgroupentry = ''
            novgroupentry = ''
            kvmgroupentry = ''

            #following are vgw configurations
            if vm_running == '1':
                vmrunninghostdomain=local('source /etc/contrail/openstackrc && nova show livemnfs |grep hypervisor_hostname|awk \'{print $4}\'', capture=True, shell='/bin/bash')
                #Take the hostname alone
                vmrunninghost = vmrunninghostdomain.split('.')[0]
                vmhost = nfs_livem_host
                #VM host should always be the nfs_livem_host
                if vmhost != vmrunninghost:
                    print 'Vm runs on a different host. Cannot continue setup'
                    return
                # The vmip is the actual ip assigned to the VM. Use this for the rest of the configurations
                vmip = local('source /etc/contrail/openstackrc && nova show livemnfs |grep \"livemnfs network\"|awk \'{print $5}\'', capture=True, shell='/bin/bash')

                for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                    if hostname == vmhost:
                        with settings(host_string = 'root@%s' %(entries), password = entry_token):
                            #Set autostart vm after node reboot
                            run('openstack-config --set /etc/nova/nova.conf DEFAULT resume_guests_state_on_host_boot True')
                            #check for vgw interface
                            vgwifrunning=run('ifconfig|grep livemnfsvgw|wc -l')
                            if vgwifrunning == '0':
                                run('vif --create livemnfsvgw --mac 00:01:5e:00:00')
                                run('ifconfig livemnfsvgw up')
                            #check and add auto start of vgw interface
                            vgwifconfig=run('cat /etc/network/interfaces | grep livemnfsvgw|wc -l')
                            if vgwifconfig == '0':
                                run('echo \"\" >> /etc/network/interfaces');
                                run('echo \"auto livemnfsvgw\" >> /etc/network/interfaces');
                                run('echo \"iface livemnfsvgw inet manual\" >> /etc/network/interfaces');
                                run('echo \"    pre-up vif --create livemnfsvgw --mac 00:01:5e:00:00\" >> /etc/network/interfaces');
                                run('echo \"    pre-up ifconfig livemnfsvgw up\" >> /etc/network/interfaces');


                            #check if we have contrail-vrouter-agent.conf for > 1.1
                            vragentconfavail=run('ls /etc/contrail/contrail-vrouter-agent.conf 2>/dev/null|wc -l', shell='/bin/bash')
                            if vragentconfavail == '1':
                                vragentconfdone=run('cat /etc/contrail/contrail-vrouter-agent.conf|grep livemnfsvgw|wc -l', shell='/bin/bash')
                                if vragentconfdone == '0':
                                    gateway_id = int('0')
                                    while True:
                                        vrgatewayavail=run('grep "\[GATEWAY-%d\]" /etc/contrail/contrail-vrouter-agent.conf |wc -l' %(gateway_id), shell='/bin/bash')
                                        if vrgatewayavail == '0':
                                            print vrgatewayavail
                                            run('openstack-config --set /etc/contrail/contrail-vrouter-agent.conf GATEWAY-%d routing_instance default-domain:admin:livemnfs:livemnfs' %(gateway_id))
                                            run('openstack-config --set /etc/contrail/contrail-vrouter-agent.conf GATEWAY-%d interface livemnfsvgw' %(gateway_id))
                                            run('openstack-config --set /etc/contrail/contrail-vrouter-agent.conf GATEWAY-%d ip_blocks %s\/%s' %(gateway_id, netaddr.IPNetwork(nfs_livem_cidr).ip, netaddr.IPNetwork(nfs_livem_cidr).prefixlen))
                                            run('service supervisor-vrouter restart' , shell='/bin/bash')
                                            break
                                        gateway_id = gateway_id + 1

                            #check for dynamic route on the vm host
                            dynroutedone=run('netstat -rn |grep %s|wc -l' %(vmip), shell='/bin/bash')
                            if dynroutedone == '0':
                                 dynroutedone=run('route add -host %s/32 dev livemnfsvgw' %(vmip), shell='/bin/bash')

                            #check and add static route on the vm host
                            staroutedone=run('cat /etc/network/interfaces |grep %s|wc -l' %(vmip), shell='/bin/bash')
                            if staroutedone == '0':
                                 run('echo \"\" >> /etc/network/interfaces');
                                 run('echo \"up route add -host %s/32 dev livemnfsvgw\" >> /etc/network/interfaces' %(vmip));

                            # Copy nova,libvirt,kvm entries
                            novapassentry=run('cat /etc/passwd |grep ^nova')
                            libqpassentry=run('cat /etc/passwd |grep ^libvirt-qemu')
                            libdpassentry=run('cat /etc/passwd |grep ^libvirt-dnsmasq')
                            novgroupentry=run('cat /etc/group |grep ^nova')
                            libgroupentry=run('cat /etc/group |grep ^kvm')
                            kvmgroupentry=run('cat /etc/group |grep ^libvirtd')

                    #add route on other nodes
                    else:
                        with settings(host_string='root@%s' %(entries),
                                        password = entry_token):
                            vhost_present=run('netstat -rn|grep vhost|wc -l',
                                                shell='/bin/bash')
                            # Nodes with vhost (computes)
                            if vhost_present != '0':

                                #check for dynamic route on the vm host
                                dynroutedone=run('netstat -rn |grep %s|wc -l'
                                                    %(vmip), shell='/bin/bash')
                                if dynroutedone == '0':
                                    dynroutedone=run('route add %s dev vhost0'
                                                    %(vmip), shell='/bin/bash')
                                #check and static route on other compute
                                staroutedone=run('cat /etc/network/interfaces '
                                                    '|grep %s|wc -l'
                                                    %(vmip), shell='/bin/bash')
                                if staroutedone == '0':
                                        run('echo \"\" >> '
                                                '/etc/network/interfaces');
                                        run('echo \"up route add %s dev '
                                                'vhost0\" >> '
                                                '/etc/network/interfaces'
                                                %(vmip));
                            # Nodes without vhost 
                            else:
                                gwentry = ''
                                for gwhostname, gwentries, sentry_token in \
                                        zip(self._args.storage_hostnames,
                                            self._args.storage_hosts,
                                            self._args.storage_host_tokens):
                                    if gwhostname == vmhost:
                                        gwentry = gwentries
                                #check for dynamic route on the vm host
                                dynroutedone=run('netstat -rn |grep %s|wc -l' %(vmip), shell='/bin/bash')
                                if dynroutedone == '0':
                                    dynroutedone=run('route add %s gw %s'
                                                        %(vmip, gwentry),
                                                        shell='/bin/bash')
                                #check and add static route on master
                                staroutedone=run('cat /etc/network/interfaces '
                                                    '|grep %s|wc -l'
                                                    %(vmip), shell='/bin/bash')
                                if staroutedone == '0':
                                        run('echo \"\" >> '
                                                '/etc/network/interfaces');
                                        run('echo \"up route add %s gw %s\" >> '
                                                '/etc/network/interfaces'
                                                %(vmip, gwentry));

                #cinder volume creation and attaching to VM
                avail=local('rados df | grep avail | awk  \'{ print $3 }\'', capture = True, shell='/bin/bash')
                # use 30% of the available space for the instances for now.
                # TODO need to check if this needs to be configurable
                avail_gb = int(avail)/1024/1024/2/3
                print avail_gb
                # update quota if available is > 1T
                if avail_gb > 1000:
                    quota_gb = avail_gb + 1000
                    admintenantid=local('source /etc/contrail/openstackrc && keystone tenant-list |grep " admin" | awk \'{print $2}\'' , capture=True, shell='/bin/bash')
                    local('source /etc/contrail/openstackrc && cinder quota-update --gigabytes=%d %s' %(quota_gb, admintenantid), capture=True, shell='/bin/bash')

                cindervolavail=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol |wc -l' , capture=True, shell='/bin/bash')
                if cindervolavail == '0':
                    #TODO might need to add a loop similar to vm start
                    local('source /etc/contrail/openstackrc && cinder create --display-name livemnfsvol --volume-type ocs-block-disk %s' %(avail_gb) , shell='/bin/bash')
                    time.sleep(5)

                    cindervolavail=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol | grep available | wc -l' , capture=True, shell='/bin/bash')

                nova_id=local('source /etc/contrail/openstackrc &&  nova list |grep livemnfs | awk \'{print $2}\'' , capture=True, shell='/bin/bash')
                cinder_id=local('source /etc/contrail/openstackrc &&  cinder list |grep livemnfsvol | awk \'{print $2}\'' , capture=True, shell='/bin/bash')
                # Check if volume is attached to the right VM
                volvmattached=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol | grep %s | wc -l' %(nova_id) , capture=True, shell='/bin/bash')
                if volvmattached == '0':
                    # Attach volume if not yet attached
                    if cindervolavail == '1':
                        local('source /etc/contrail/openstackrc && nova volume-attach %s %s /dev/vdb' %(nova_id, cinder_id) , capture=True, shell='/bin/bash')
                    while True:
                        print 'Waiting for volume to be attached to VM'
                        time.sleep(5)
                        volvmattached=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol | grep %s | wc -l' %(nova_id) , capture=True, shell='/bin/bash')
                        if volvmattached == '1':
                            break
                if volvmattached == '0':
                    return

                while True:
                    vmavail=local('ping -c 1 %s | grep \" 0%% packet loss\" |wc -l' %(vmip) , capture=True, shell='/bin/bash')
                    if vmavail == '1':
                        break
                    print 'Waiting for VM to come up'
                    time.sleep(10)
                with settings(host_string = 'livemnfs@%s' %(vmip), password = 'livemnfs'):
                    mounted=run('sudo cat /proc/mounts|grep livemnfs|wc -l')
                    if mounted == '0':
                        while True:
                            vdbavail=run('sudo fdisk -l /dev/vdb |grep vdb|wc -l')
                            if vdbavail == '0':
                                print 'Disk not available yet. Need to reboot VM'
                                vdbavail=run('sudo reboot')
                                time.sleep(10)
                                while True:
                                    print 'Waiting for VM to come up'
                                    time.sleep(10)
                                    vmavail=local('ping -c 1 %s | grep \" 0%% packet loss\" |wc -l' %(vmip) , capture=True, shell='/bin/bash')
                                    if vmavail == '1':
                                        time.sleep(10)
                                        break
                            else:
                                break
                        vdbavail=run('sudo parted /dev/vdb print |grep ext4|wc -l')
                        if vdbavail == '0':
                            run('sudo parted -s /dev/vdb mklabel gpt')
                            vdbsize=run('sudo parted /dev/vdb print | \
                                        grep Disk|awk \'{print $3}\'')
                            run('sudo parted -s /dev/vdb mkpart primary 1M %s'
                                        %(vdbsize))
                            run('sudo mkfs.ext4  /dev/vdb1')
                        run('sudo rm -rf /livemnfsvol')
                        run('sudo mkdir /livemnfsvol')
                        run('sudo mount /dev/vdb1 /livemnfsvol')
                        #Add to /etc/fstab for automount

                        while True:
                            vdbuuid=run('ls -l /dev/disk/by-uuid/ |grep vdb1|awk \'{print $9}\'', shell='/bin/bash')
                            if vdbuuid != '':
                                break
                            time.sleep(1)

                        vdbfstab=run('cat /etc/fstab | grep %s| wc -l' %(vdbuuid))
                        if vdbfstab == '0':
                            run('sudo cp /etc/fstab /tmp/fstab')
                            run('sudo chmod  666 /tmp/fstab')
                            run('echo \"# /livemnfsvol on /dev/vdb1\" >> /tmp/fstab')
                            run('echo \"UUID=%s /livemnfsvol ext4 rw,noatime,data=writeback,barrier=0,nobh,errors=remount-ro 0 0\" >> /tmp/fstab' %(vdbuuid))
                            run('sudo chmod  644 /tmp/fstab')
                            run('sudo mv /tmp/fstab /etc/fstab')

                    novaentry=run('sudo cat /etc/passwd|grep ^nova|wc -l')
                    if novaentry == '0':
                        run('sudo cp /etc/passwd /tmp/passwd')
                        run('sudo chmod  666 /tmp/passwd')
                        run('sudo echo \"%s\" >> /tmp/passwd' %(novapassentry))
                        run('sudo echo \"%s\" >> /tmp/passwd' %(libqpassentry))
                        run('sudo echo \"%s\" >> /tmp/passwd' %(libdpassentry))
                        run('sudo chmod  644 /tmp/passwd')
                        run('sudo mv -f /tmp/passwd /etc/passwd')
                        run('sudo cp /etc/group /tmp/group')
                        run('sudo chmod  666 /tmp/group')
                        run('sudo echo \"%s\" >> /tmp/group' %(novgroupentry))
                        run('sudo echo \"%s\" >> /tmp/group' %(libgroupentry))
                        run('sudo echo \"%s\" >> /tmp/group' %(kvmgroupentry))
                        run('sudo chmod  644 /tmp/group')
                        run('sudo mv -f /tmp/group /etc/group')
                        run('sudo chown -R nova:nova /livemnfsvol')
                    nfsexports=run('sudo cat /etc/exports |grep livemnfsvol|wc -l')
                    if nfsexports == '0':
                        run('sudo cp /etc/exports /tmp/exports')
                        run('sudo chmod  666 /tmp/exports')
                        run('sudo echo \"/livemnfsvol *(rw,async,no_subtree_check,no_root_squash)\" >> /tmp/exports')
                        run('sudo chmod  644 /tmp/exports')
                        run('sudo mv -f /tmp/exports /etc/exports')
                        run('sync')
                        # restarting the vm for now. - need to check this out.
                        # need to do this only if the mounts are not done in the hosts
                    nfsrunning=run('sudo exportfs |grep livemnfsvol|wc -l')
                    if nfsexports == '0' or nfsrunning == '0':
                        run('sudo  service nfs-kernel-server restart > /tmp/nfssrv.out', shell='/bin/bash')
                        time.sleep(2)
                        vdbavail=run('sudo reboot')
                        time.sleep(10)
                        while True:
                            print 'Waiting for VM to come up'
                            time.sleep(10)
                            vmavail=local('ping -c 1 %s | grep \" 0%% packet loss\" |wc -l' %(vmip) , capture=True, shell='/bin/bash')
                            if vmavail == '1':
                                time.sleep(10)
                                break

                for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                    # Not sure if mount in master is required
                    # if entries != self._args.storage_master:
                    with settings(host_string = 'root@%s' %(entries), password = entry_token):
                        # Add to fstab to auto-mount the nfs file system upon
                        # reboot. The 'bg' option takes care of retrying mount
                        # if the vm is not reachable.
                        fstab_added=run('sudo cat %s | grep livemnfsvol | wc -l' %(ETC_FSTAB))
                        if fstab_added == '0':
                            run('sudo echo \"%s:/livemnfsvol %s nfs rw,bg,soft 0 0\" >> %s' %(vmip, NOVA_INST_GLOBAL, ETC_FSTAB))
                        mounted=run('sudo cat /proc/mounts | grep livemnfsvol|wc -l')
                        if mounted == '0':
                            print mounted
                            run('ping -c 10 %s' %(vmip))
                            run('sudo rm -rf /var/lib/nova/instances/global')
                            run('sudo mkdir /var/lib/nova/instances/global')
                            run('sudo mount %s:/livemnfsvol /var/lib/nova/instances/global' %(vmip))
                            if entries != self._args.storage_master:
                                run('sudo chown nova:nova /var/lib/nova/instances/global')
                        else:
                            run('ping -c 10 %s' %(vmip))
                            stalenfs=run('ls /var/lib/nova/instances/global 2>&1 | grep Stale|wc -l')
                            if stalenfs == '1':
                                run('sudo umount /var/lib/nova/instances/global')
                                run('sudo mount %s:/livemnfsvol /var/lib/nova/instances/global' %(vmip))
                                if entries != self._args.storage_master:
                                    run('sudo chown nova:nova /var/lib/nova/instances/global')

            if self._args.storage_setup_mode == 'setup_global':
                for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                    if entries != self._args.storage_master:
                        with settings(host_string = 'root@%s' %(entries), password = entry_token):
                            #Set autostart vm after node reboot
                            run('openstack-config --set /etc/nova/nova.conf DEFAULT storage_scope global')
                            run('sudo service nova-compute restart')

        if self._args.storage_setup_mode == 'unconfigure':
            # Unconfigure started
            # Umount /var/lib/nova/instances/global from all the nodes
            for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                # Not sure if mount in master is required
                # if entries != self._args.storage_master:
                with settings(host_string = 'root@%s' %(entries), password = entry_token):
                    fstab_added=run('sudo cat %s | grep livemnfsvol | wc -l' %(ETC_FSTAB))
                    if fstab_added == '1':
                        run('sudo rm -rf %s' %(TMP_FSTAB))
                        run('sudo cat %s | grep -v livemnfsvol >> %s' %(ETC_FSTAB, TMP_FSTAB))
                        run('sudo mv %s %s' %(TMP_FSTAB, ETC_FSTAB))
                    mounted=run('cat /proc/mounts | grep livemnfsvol|wc -l')
                    if mounted == '1':
                        mountused=run('lsof /var/lib/nova/instances/global | wc -l');
                        if mountused != '0':
                            print '/var/lib/nova/instance/global is being used, Cannot unconfigure'
                            return
                        else:
                            run('sudo umount /var/lib/nova/instances/global')

            vmip = ''
            # Stop NFS Server and unmount the cinder volume inside the VM
            vm_running=local('source /etc/contrail/openstackrc && nova list | grep livemnfs |grep ACTIVE |wc -l' , capture=True, shell='/bin/bash')
            if vm_running != '0':
                vmip = local('source /etc/contrail/openstackrc && nova show livemnfs |grep \"livemnfs network\"|awk \'{print $5}\'', capture=True, shell='/bin/bash')
                nova_id=local('source /etc/contrail/openstackrc &&  nova list |grep livemnfs | awk \'{print $2}\'' , capture=True, shell='/bin/bash')
                volvmattached=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol | grep %s | wc -l' %(nova_id) , capture=True, shell='/bin/bash')
                vmavail=local('ping -c 1 %s | grep \" 0%% packet loss\" |wc -l' %(vmip) , capture=True, shell='/bin/bash')
                if vmavail == '1':
                    if volvmattached != '0':
                        with settings(host_string = 'livemnfs@%s' %(vmip), password = 'livemnfs'):
                            run('sudo service nfs-kernel-server stop > /tmp/nfssrv.out', shell='/bin/bash')
                            mounted=run('sudo cat /proc/mounts | grep livemnfsvol | wc -l');
                            if mounted == '1':
                                run('sudo umount -f /livemnfsvol')
                cinder_id=local('source /etc/contrail/openstackrc &&  cinder list |grep livemnfsvol | awk \'{print $2}\'' , capture=True, shell='/bin/bash')
                if volvmattached != '0':
                    local('source /etc/contrail/openstackrc && nova volume-detach %s %s' %(nova_id, cinder_id) , capture=True, shell='/bin/bash')
                while True:
                    volvmattached=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol | grep %s | wc -l' %(nova_id) , capture=True, shell='/bin/bash')
                    if volvmattached == '0':
                        break;
                    else:
                        print 'Waiting for volume to be detached'
                        time.sleep(5)

            cinder_id=local('source /etc/contrail/openstackrc &&  cinder list |grep livemnfsvol | awk \'{print $2}\'' , capture=True, shell='/bin/bash')
            # Detach the cinder volume and delete it
            cindervolavail=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol |wc -l' , capture=True, shell='/bin/bash')
            if cindervolavail != '0':
                local('source /etc/contrail/openstackrc && cinder delete %s' %(cinder_id) , shell='/bin/bash')
                while True:
                    cindervolavail=local('source /etc/contrail/openstackrc && cinder list | grep livemnfsvol |wc -l' , capture=True, shell='/bin/bash')
                    if cindervolavail == '0':
                        break;
                    else:
                        print 'Waiting for volume to be deleted'
                        time.sleep(5)

            # Revert all the VGW configuration done and remove all the dynamic
            # and static routes from all the nodes
            vmhost = nfs_livem_host

            # if vmip is not set, means someone has deleted the vm
            # Get the vmip from the interfaces configuration
            if vmip == '':
                for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                    if hostname == vmhost:
                        with settings(host_string = 'root@%s' %(entries), password = entry_token):
                            vmipavail=run('cat /etc/network/interfaces |grep livemnfsvgw| grep route| wc -l')
                            if vmipavail == '0':
                                print 'no nfs livemigration configuration found'
                                return
                            vmipcidr=run('cat /etc/network/interfaces |grep livemnfsvgw| grep route| awk \'{print $5}\'', shell='/bin/bash')
                            vmip=vmipcidr.split('/')[0]
                            # Still cannot find vmip, return
                            if vmip == '':
                                print 'Cannot find vm ip. Cannot continue unconfigure'
                                return

            for hostname, entries, entry_token in zip(self._args.storage_hostnames, self._args.storage_hosts, self._args.storage_host_tokens):
                if hostname == vmhost:
                    with settings(host_string = 'root@%s' %(entries), password = entry_token):

                        #check if we have contrail-vrouter-agent.conf for > 1.1
                        vragentconfavail=run('ls /etc/contrail/contrail-vrouter-agent.conf 2>/dev/null|wc -l', shell='/bin/bash')
                        if vragentconfavail == '1':
                            vragentconfdone=run('cat /etc/contrail/contrail-vrouter-agent.conf|grep livemnfsvgw|wc -l', shell='/bin/bash')
                            if vragentconfdone == '1':
                                gateway_id = int('0')
                                while True:
                                    gateway_avail = run('grep -n "^\[GATEWAY-%d\]" /etc/contrail/contrail-vrouter-agent.conf | wc -l' %(gateway_id), shell='/bin/bash')
                                    if gateway_avail != '0':
                                        gateway_line_string = run('grep -n "^\[GATEWAY-%d\]" /etc/contrail/contrail-vrouter-agent.conf' %(gateway_id), shell='/bin/bash')
                                        gateway_line_num = int(gateway_line_string.split(':')[0])
                                        rtinst_line_string = run('grep -n "^routing_instance = default-domain:admin:livemnfs:livemnfs" /etc/contrail/contrail-vrouter-agent.conf', shell='/bin/bash')
                                        rtinst_line_num = int(rtinst_line_string.split(':')[0])
                                        if rtinst_line_num == (gateway_line_num + 1):
                                            run('openstack-config --del /etc/contrail/contrail-vrouter-agent.conf GATEWAY-%d' %(gateway_id))
                                            run('service supervisor-vrouter restart' , shell='/bin/bash')
                                            break
                                    gateway_id = gateway_id + 1

                        #check for dynamic route on the vm host
                        dynroutedone=run('netstat -rn |grep %s|wc -l' %(vmip), shell='/bin/bash')
                        if dynroutedone == '1':
                             dynroutedone=run('route del -host %s/32 dev livemnfsvgw' %(vmip), shell='/bin/bash')

                        #check and delete static route on the vm host
                        staroutedone=run('cat /etc/network/interfaces |grep %s|wc -l' %(vmip), shell='/bin/bash')
                        if staroutedone == '1':
                            staroutedone=run('cat /etc/network/interfaces |grep -v livemnfsvgw > /tmp/interfaces', shell='/bin/bash')
                            run('cp /tmp/interfaces /etc/network/interfaces');

                #delete route on other nodes
                else:
                    with settings(host_string = 'root@%s' %(entries),
                                    password = entry_token):
                        vhost_present=run('netstat -rn|grep vhost |wc -l',
                                            shell='/bin/bash')
                        if vhost_present != '0':
                            #check for dynamic route on the vm host
                            dynroutedone=run('netstat -rn |grep %s|wc -l'
                                                %(vmip), shell='/bin/bash')
                            if dynroutedone == '1':
                                dynroutedone=run('route del %s dev vhost0'
                                                    %(vmip), shell='/bin/bash')
                            #check and static route on other compute
                            staroutedone=run('cat /etc/network/interfaces '
                                                '|grep %s|wc -l'
                                                %(vmip), shell='/bin/bash')
                            if staroutedone == '1':
                                staroutedone=run('cat /etc/network/interfaces '
                                                    '|grep -v %s > '
                                                    '/tmp/interfaces'
                                                    %(vmip), shell='/bin/bash')
                                run('cp /tmp/interfaces /etc/network/interfaces');
                        else:

                            gwentry = ''
                            for gwhostname, gwentries, sentry_token in \
                                zip(self._args.storage_hostnames,
                                    self._args.storage_hosts,
                                    self._args.storage_host_tokens):
                                if gwhostname == vmhost:
                                    gwentry = gwentries
                            #check for dynamic route on the vm host
                            dynroutedone=run('netstat -rn |grep %s|wc -l'
                                                %(vmip), shell='/bin/bash')
                            if dynroutedone == '1':
                                dynroutedone=run('route del %s gw %s'
                                                    %(vmip, gwentry),
                                                    shell='/bin/bash')
                            #check and delete static route on master
                            staroutedone=run('cat /etc/network/interfaces '
                                                '|grep %s|wc -l'
                                                %(vmip), shell='/bin/bash')
                            if staroutedone == '1':
                                staroutedone=run('cat /etc/network/interfaces '
                                                    '|grep -v %s > '
                                                    '/tmp/interfaces'
                                                    %(vmip), shell='/bin/bash')
                                run('cp /tmp/interfaces /etc/network/interfaces');

            # Delete the VM
            vm_running=local('source /etc/contrail/openstackrc && nova list | grep livemnfs |wc -l' , capture=True, shell='/bin/bash')
            if vm_running == '1':
                local('source /etc/contrail/openstackrc && nova delete livemnfs', shell='/bin/bash')

            while True:
                vm_running=local('source /etc/contrail/openstackrc && nova list | grep livemnfs |wc -l' , capture=True, shell='/bin/bash')
                if vm_running == '0':
                    break;
                else:
                    print 'Waiting for VM to be destroyed'
                    time.sleep(5)

            vmflavor = local('source /etc/contrail/openstackrc && nova flavor-list | grep nfsvm_flavor | wc -l', capture=True, shell='/bin/bash')
            if vmflavor != '0':
                local('source /etc/contrail/openstackrc &&  nova flavor-delete nfsvm_flavor', shell='/bin/bash')

            #delete the neutron subnet
            neutronsubnet=local('source /etc/contrail/openstackrc && neutron subnet-list | grep %s |wc -l' %(nfs_livem_cidr), capture=True, shell='/bin/bash')
            if neutronsubnet == '1':
                subnet_id = livemnfs=local('source /etc/contrail/openstackrc && neutron subnet-list |grep %s| awk \'{print $2}\'' %(nfs_livem_cidr), capture=True, shell='/bin/bash')
                local('source /etc/contrail/openstackrc && neutron subnet-delete %s 2&> /dev/null' %(subnet_id), shell='/bin/bash')

            #delete the neutron net
            neutronnet=local('source /etc/contrail/openstackrc && neutron net-list | grep livemnfs|wc -l', capture=True, shell='/bin/bash')
            if neutronnet == '1':
                local('source /etc/contrail/openstackrc && neutron net-delete livemnfs', shell='/bin/bash')
            livemnfs=local('source /etc/contrail/openstackrc && /usr/bin/glance image-list | grep livemnfs|wc -l', capture=True, shell='/bin/bash')
            if livemnfs == '1':
                local('source /etc/contrail/openstackrc && /usr/bin/glance image-delete livemnfs', capture=True, shell='/bin/bash')

    #end __init__

    def _parse_args(self, args_str):
        '''
        Eg. python nfslivem-ceph-setup.py --storage-master 10.157.43.171 --storage-hostnames cmbu-dt05 cmbu-ixs6-2 --storage-hosts 10.157.43.171 10.157.42.166 --storage-host-tokens n1keenA n1keenA --storage-disk-config 10.157.43.171:sde 10.157.43.171:sdf 10.157.43.171:sdg --storage-directory-config 10.157.42.166:/mnt/osd0 --live-migration enabled --nfs-livem-subnet 192.168.10.0/24 --nfs-livem-image /opt/contrail/contrail_installer/livemnfs.qcow2
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help = False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        global_defaults = {
        }

        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            global_defaults.update(dict(config.items("GLOBAL")))

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

        all_defaults = {'global': global_defaults}
        parser.set_defaults(**all_defaults)

        parser.add_argument("--storage-master", help = "IP Address of storage master node")
        parser.add_argument("--storage-hostnames", help = "Host names of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-hosts", help = "IP Addresses of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-host-tokens", help = "Passwords of storage nodes", nargs='+', type=str)
        parser.add_argument("--storage-disk-config", help = "Disk list to be used for distrubuted storage", nargs="+", type=str)
        parser.add_argument("--storage-directory-config", help = "Directories to be sued for distributed storage", nargs="+", type=str)
        parser.add_argument("--nfs-livem-subnet", help = "subnet for nfs live migration vm", nargs="+", type=str)
        parser.add_argument("--nfs-livem-image", help = "image for nfs live migration vm", nargs="+", type=str)
        parser.add_argument("--nfs-livem-host", help = "host for nfs live migration vm", nargs="+", type=str)
        parser.add_argument("--storage-setup-mode", help = "Storage configuration mode")

        self._args = parser.parse_args(remaining_argv)

    #end _parse_args

#end class SetupCeph

def main(args_str = None):
    SetupNFSLivem(args_str)
#end main

if __name__ == "__main__":
    main()
