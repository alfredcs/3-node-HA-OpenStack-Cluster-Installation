#!/usr/bin/env bash

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


CONF_DIR=/etc/contrail
set -x

if [ -f /etc/redhat-release ]; then
   is_redhat=1
   is_ubuntu=0
   web_svc=httpd
fi

if [ -f /etc/lsb-release ] && egrep -q 'DISTRIB_ID.*Ubuntu' /etc/lsb-release; then
   is_ubuntu=1
   is_redhat=0
   web_svc=apache2
fi

# Create link /usr/bin/nodejs to /usr/bin/node
if [ ! -f /usr/bin/nodejs ]; then 
    ln -s /usr/bin/node /usr/bin/nodejs
fi

echo "======= Enabling the services ======"

for svc in rabbitmq-server $web_svc memcached; do
    chkconfig $svc on
done

for svc in supervisor-config quantum-server puppetmaster; do
    chkconfig $svc on
done

echo "======= Starting the services ======"

for svc in rabbitmq-server $web_svc memcached; do
    service $svc restart
done

for svc in puppetmaster; do
    service $svc restart
done

# TODO: move dependency to service script
# wait for ifmap server to start
tries=0
while [ $tries -lt 10 ]; do
    wget -O- http://localhost:8443 >/dev/null 2>&1
    if [ $? -eq 0 ]; then break; fi
    tries=$(($tries + 1))
    sleep 1
done

chkconfig supervisor-config on
service supervisor-config restart

#service quantum-server restart

