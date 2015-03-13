#!/usr/bin/env bash

CONF_DIR=/etc/contrail
set -x

# Generate Service Token

if [ -f $CONF_DIR/service.token ]; then
  echo "Service Password Exist! Please delete it first"
  exit
fi

SERVICE_PASSWORD=$(openssl rand -hex 10)
echo -n $SERVICE_PASSWORD > $CONF_DIR/service.token
chmod 400 $CONF_DIR/service.token

