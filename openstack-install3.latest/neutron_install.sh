#!/bin/bash
set -x
function usage() {
cat <<EOF
usage: $0 options

This script will install neutron endpoint on Keystone

Example:
        neutron_install.sh [-L] -v contrail_controller_vip -F first_openstack_controller [-u neutron_keyston_passwd]

OPTIONS:
  -h -- Help Show this message
  -F -- The first contrail controller's IP address
  -L -- Use SSL for keystone
  -S -- The second contrail controller's IP address
  -u -- Neutron keystone password
  -V -- Verbose Verbose output
  -v -- VIP of the openstack controller

EOF
}
FIRST_CONTROLLER=""
KEYSTONE_CMD=keystone
HTTP_CMD=http
[[ `id -u` -ne 0 ]] && { echo  "Must be root!"; exit 0; }
[[ $# -lt 1 ]] && { usage; exit 1; }
while getopts "hF:Lu:v:VD" OPTION; do
case "$OPTION" in
h)
        usage
        exit 0
        ;;
F)
        FIRST_CONTROLLER="$OPTARG"
        ;;
L)
        KEYSTONE_CMD="keystone --insecure"
        HTTP_CMD="https"
        ;;
u)
	NEUTRON_PASS="$OPTARG"
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
local_controller=`egrep $HOSTNAME /etc/hosts|grep -v ^#|head -1|awk '{print $1}'`
if [[  ${FIRST_CONTROLLER} == ${local_controller}  ]]; then
        echo "Installing Glance on the firsth Openstack controller node ......"
else
        ###
        # Get Keys
        ###
        #[[ -f .keystone_grants ]] && { rm -rf .keystone_grants; rm -rf eystone_grants.enc; }
        #curl --insecure -o keystone_grants.enc https://${FIRST_CONTROLLER}/.tmp/keystone_grants.enc
        #[[  -f keystone/newkey.pem && -f keystone_grants.enc ]] && openssl rsautl -decrypt -inkey keystone/newkey.pem -in keystone_grants.enc -out .keystone_grants
        [[ ! -f  ./.keystone_grants ]] && { echo "Require credential file from Openstacl installation!"; exit 1; }
fi

NEUTRON_KSPASS=${NEUTRON_KSPASS:-`cat ./.keystone_grants|grep -i NEUTRON_KSPASS| grep -v ^#|cut -d= -f2`}
controller=${controller:-`cat ./.keystone_grants|grep -i openstack_controller| grep -v ^#|cut -d= -f2`}
domain_name=`echo $HOSTNAME|cut -d\. -f2,3,4,5`
domain_name=${domain_name:-"default.domain"}
[[ -f ~/contrc ]] && source ~/contrc
if [[ ${FIRST_CONTROLLER} == ${local_controller} ]]; then
	if [ `${KEYSTONE_CMD} user-list| grep neutron | wc -l` -lt 1 ]; then
        	${KEYSTONE_CMD} user-create --name=neutron --pass=$NEUTRON_PASS --email=neutron@$domain_name
        	${KEYSTONE_CMD} user-role-add --user=neutron --tenant=service --role=admin
	fi
	[ `${KEYSTONE_CMD} service-list | grep neutron | wc -l` -lt 1 ] && ${KEYSTONE_CMD} service-create --name=neutron --type=image --description="Neutron Image Service"
	NEUTRON_SERVICE_ID=`${KEYSTONE_CMD} service-list | grep -i neutron|awk '{print $2}'`
	[ `${KEYSTONE_CMD} endpoint-list | grep $NEUTRON_SERVICE_ID | wc -l ` -lt 1 ] && ${KEYSTONE_CMD} endpoint-create --service-id=`${KEYSTONE_CMD} service-list|grep neutron|awk '{print $2}'` --publicurl=${HTTP_CMD}://${openstack_controller}:9696 --internalurl=${HTTP_CMD}://${openstack_controller}:9696 --adminurl=${HTTP_CMD}://${openstack_controller}:9696
fi
