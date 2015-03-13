#!/bin/bash
set -x
function usage() {
cat <<EOF
usage: $0 options

This script will Horizon on a Openstack controller

Example:
        horizon_install.sh [-L] -v openstack_controller_vip -F first_openstack_controller

OPTIONS:
  -h -- Help Show this message
  -F -- The first contrail controller's IP address
  -L -- SSL for Keystone
  -S -- The second contrail controller's IP addressd
  -V -- Verbose Verbose output
  -v -- VIP of the openstack controller

EOF
}
FIRST_CONTROLLER=""
HTTP_CMD=http
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
while getopts "hLF:v:VD" OPTION; do
case "$OPTION" in
h)
        usage
        exit 0
        ;;
F)
	first_openstack_controller="$OPTARG"
	;;
L)
	HTTP_CMD="https"
	;;
v)
        openstack_controller="$OPTARG"
        ;;
V)
        display_version
        exit 0
        ;;
D)
        DEBUG=1
        ;;
\?)
        echo "Invalid option: -"$OPTARG"" >&2
        usage
        exit 1
        ;;
:)
        usage
        exit 1
        ;;
esac
done

local_controller=`egrep $HOSTNAME /etc/hosts|grep -v ^#|awk '{print $1}'`
if [[  ${first_openstack_controller} == ${local_controller}  ]]; then
        echo "Installing Glance on the firsth Openstack controller node ......"
else
        ###
        # Get Keys
        ###
        #[[ -f .keystone_grants ]] && { rm -rf .keystone_grants; rm -rf eystone_grants.enc; }
        #curl --insecure -o keystone_grants.enc https://${first_openstack_controller}/.tmp/keystone_grants.enc
        #[[  -f keystone/newkey.pem && -f keystone_grants.enc ]] && openssl rsautl -decrypt -inkey keystone/newkey.pem -in keystone_grants.enc -out .keystone_grants
        [[ ! -f  ./.keystone_grants ]] && { echo "Require credential file from Openstacl installation!"; exit 1; }
fi

openstack_controller=${openstack_controller:-`cat ./.keystone_grants|grep -i openstack_controller| grep -v ^#|cut -d= -f2`}

[[ `rpm -qa | grep openstack-dashboard|wc -l` -gt 0 ]] && rpm -e --nodeps `rpm -qa|egrep 'mod_ssl|mod_wsgi|openstack-dashboard|python-django-openstack-auth'`
yum -y install --disablerepo=* --enablerepo=havana_install_repo110 openstack-dashboard mod-wsgi mod_ssl python-django-openstack-auth
[[ -f horizon/local_settings.controller ]] && /bin/cp -fp horizon/local_settings.controller /etc/openstack-dashboard/local_settings
[[ -f horizon/openstack-dashboard.conf.controller ]] && /bin/cp -fp horizon/openstack-dashboard.conf.controller /etc/httpd/conf.d/openstack-dashboard.conf
sed -i "s/controller/${openstack_controller}/g" /etc/openstack-dashboard/local_settings
sed -i "s/controller/${openstack_controller}/g" /etc/httpd/conf.d/openstack-dashboard.conf
sed -i "s/http_cmd/${HTTP_CMD}/g" /etc/openstack-dashboard/local_settings
chkconfig memcached on
chkconfig httpd on
service memcached restart
service httpd restart
