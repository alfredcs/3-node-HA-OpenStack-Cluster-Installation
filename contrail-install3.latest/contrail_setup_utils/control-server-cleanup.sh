#!/usr/bin/env bash
supervisorctl -s http://localhost:9003 stop contrail-control
supervisorctl -s http://localhost:9003 stop contrail-dns
supervisorctl -s http://localhost:9003 stop contrail-named
chkconfig supervisor-control off
service supervisor-control stop
