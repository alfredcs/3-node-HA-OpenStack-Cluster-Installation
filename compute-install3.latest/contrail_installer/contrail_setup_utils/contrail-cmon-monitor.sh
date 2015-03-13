#!/bin/bash

# Purpose of the script is to check the state of galera cluster
# Author - Sanju Abraham

source /etc/contrail/ha/cmon_param

LOGFILE=/var/log/contrail/ha/cmon-monitor.log
MYIPS=$(ip a s|sed -ne '/127.0.0.1/!{s/^[ \t]*inet[ \t]*\([0-9.]\+\)\/.*$/\1/p}')
RUN_STATE="isrunning"
CMON_SVC_CHECK="service cmon status"
RUN_CMON="service cmon start"
STOP_CMON="service cmon stop"
MYSQL_SVC_CHECK="service mysql status"
HAP_RESTART="service haproxy restart"
ARP_CACHE_FLUSH="arp -d $VIP"
cmon_run=0
viponme=0
haprestart=0
RMQ_MONITOR="/opt/contrail/bin/contrail-rmq-monitor.sh"
NOVA_SCHED_CHK="supervisorctl -s http://localhost:9010 status nova-scheduler"
NOVA_CONS_CHK="supervisorctl -s http://localhost:9010 status nova-console"
NOVA_CONSAUTH_CHK="supervisorctl -s http://localhost:9010 status nova-consoleauth"
NOVA_SCHED_RST="service nova-scheduler restart"
NOVA_CONS_RST="service nova-console restart"
NOVA_CONSAUTH_RST="service nova-consoleauth restart"
NOVA_COND_STOP="service nova-conductor stop"
NOVA_COND_START="service nova-conductor start"
NOVA_COND_STATUS="service nova-conductor status"
NOVA_SCHED_STOP="service nova-conductor stop"
NOVA_SCHED_START="service nova-conductor start"
NOVA_SCHED_STATUS="service nova-scheduler status"
NOVA_RUN_STATE="RUNNING"
STATE_EXITED="EXITED"
STATE_FATAL="FATAL"

timestamp() {
    date +"%T"
}

log_error_msg() {
    msg=$1
    echo "$(timestamp): ERROR: $msg" >> $LOGFILE
}

log_warn_msg() {
    msg=$1
    echo "$(timestamp): WARNING: $msg" >> $LOGFILE
}

log_info_msg() {
    msg=$1
    echo "$(timestamp): INFO: $msg" >> $LOGFILE
}

for y in $MYIPS
 do
  if [ $y == $VIP ]; then
     viponme=1
     log_info_msg "VIP - $VIP is on this node"
     break
  fi
 done

verify_mysql() {
   mysqlsvc=$($MYSQL_SVC_CHECK | awk '{print $3 $4}') 
   mysqlpid=$(pidof mysqld)
   if [ $mysqlsvc == $RUN_STATE ] && [ -n "$mysqlpid" ]; then
      log_info_msg "MySQL is Running"
      echo "y"
      return 1
   else
      log_info_msg "MySQL is not Running"
      echo "n"
      return 0
   fi
   exit 1
}

verify_cmon() {
   cmon=$($CMON_SVC_CHECK | awk '{print $2 $3}')
   cmonpid=$(pidof cmon)
   if [ $cmon == $RUN_STATE ] && [ -n "$cmonpid" ]; then
      log_info_msg "CMON is Running"
      echo "y"
      return 1
   else
      log_info_msg "CMON is not Running"
      echo "n"
      return 0
   fi
}

verify_nova_cond() {
  cond=$($NOVA_COND_STATUS | awk '{print $2}')
  if [ $cond == $NOVA_RUN_STATE ]; then
     echo "y"
     return 1
  else
     echo "n"
     return 0
  fi
}

verify_nova_sched() {
  sched=$($NOVA_SCHED_STATUS | awk '{print $2}')
  if [ $sched == $NOVA_RUN_STATE ]; then
     echo "y"
     return 1
  else
     echo "n"
     return 0
  fi
}
cmon_run=$(verify_cmon)
# Check for cmon and if its the VIP node let cmon run or start it
if [ $viponme -eq 1 ]; then
   if [ $cmon_run == "n" ]; then
      (exec $RUN_CMON)&
      log_info_msg "Started CMON on detecting VIP"

      for (( i=0; i<${COMPUTES_SIZE}; i++ ))
       do
        (exec ssh -o StrictHostKeyChecking=no "$COMPUTES_USER@${COMPUTES[i]}" "$ARP_CACHE_FLUSH")&
        log_info_msg "ARP clean up for VIP on ${COMPUTES[i]}"
       done

       for (( i=0; i<${DIPS_SIZE}; i++ ))
        do
         (exec ssh -o StrictHostKeyChecking=no "$COMPUTES_USER@${DIPS[i]}" "$ARP_CACHE_FLUSH")&
         log_info_msg "ARP clean up for VIP on ${DIPS[i]}"
        done
       
       (exec $RMQ_MONITOR)& 
    fi
   # Check periodically for RMQ status
   if [[ -n "$PERIODIC_RMQ_CHK_INTER" ]]; then
      sleep $PERIODIC_RMQ_CHK_INTER
      (exec $RMQ_MONITOR)&
   fi
else
   if [ $cmon_run == "y" ]; then
      (exec $STOP_CMON)&
      log_info_msg "Stopped CMON on not finding VIP"

      #Check if the VIP was on this node and clear all session by restarting haproxy
      hapid=$(pidof haproxy)
      for (( i=0; i<${DIPS_SIZE}; i++ ))
      do
        dipsonnonvip=$(lsof -p $hapid | grep ${DIPS[i]} | awk '{print $9}')
        if [[ -n "$dipsonnonvip" ]]; then
         haprestart=1
         break
        fi
      done

      if [ $haprestart -eq 1 ]; then
       (exec $HAP_RESTART)&
       log_info_msg "Restarted HAP becuase of stale dips"
      fi
   fi
fi
      
  # These checks will eventually be replaced when we have nodemgr plugged in
  # for openstack services
  # CHECK FOR NOVA SCHD
  state=$($NOVA_SCHED_CHK | awk '{print $2}')
  if [ "$state" == "$STATE_EXITED" ] || [ "$state" == "$STATE_FATAL" ]; then
     (exec $NOVA_SCHED_RST)&
     log_info_msg "Nova Scheduler restarted becuase of the state $state"
  fi

  # CHECK FOR NOVA CONS
  state=$($NOVA_CONS_CHK | awk '{print $2}')
  if [ "$state" == "$STATE_EXITED" ] || [ "$state" == "$STATE_FATAL" ]; then
     (exec $NOVA_CONS_RST)&
     log_info_msg "Nova Console restarted becuase of the state $state"
  fi

  # CHECK FOR NOVA CONSAUTH
  state=$($NOVA_CONSAUTH_CHK | awk '{print $2}')
  if [ "$state" == "$STATE_EXITED" ] || [ "$state" == "$STATE_FATAL" ]; then
     (exec $NOVA_CONSAUTH_RST)&
     log_info_msg "Nova ConsoleAuth restarted becuase of the state $state"
  fi

  mysql_run=$(verify_mysql)
  cond_run=$(verify_nova_cond)
  sched_run=$(verify_nova_sched)
  if [ $mysql_run == "n" ]; then
     (exec $NOVA_COND_STOP)&
     (exec $NOVA_SCHED_STOP)&
     log_info_msg "Stopped conductor and scheduler becuase of Mysql dependency.
                   Requests will be processed by other conductors and schedulers"
  elif [ $mysql_run == "y" ]; then
      if [ $cond_run == "n" ]; then
         (exec $NOVA_COND_START)&
         log_info_msg "Starting conductor after detecting mysql status"
      fi
      if [ $sched_run == "n" ]; then
         (exec $NOVA_SCHED_START)&
         log_info_msg "Starting scheduler after detecting mysql status"
      fi
  fi

exit 0
