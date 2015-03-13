#!/usr/bin/env bash

#setup script for analytics package under supervisord
chkconfig supervisor-analytics on
service supervisor-analytics restart

