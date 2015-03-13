#!/usr/bin/env bash

#setup script for webui package under supervisord
chkconfig supervisor-webui on
service supervisor-webui restart

