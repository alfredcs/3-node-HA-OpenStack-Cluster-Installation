#!/bin/bash
#
# Script to be trrigerd by rc.local to bootstrap galera cluster on every reboot of all galera nodes in the cluster.

LOGFILE=/var/log/galera-bootstrap.log
RETRIES=3
MYIDFILE="/etc/contrail/galeraid"
RETRY_TIMEOUT=60
RETRY_INTERVAL=5

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
    
verify_mysql() {
    retry_count=$(($RETRY_TIMEOUT / RETRY_INTERVAL))
    for i in $(eval echo {1..$retry_count}); do
        sleep $RETRY_INTERVAL
        pid=$(pidof mysqld)
        if [ "$pid" == '' ]; then
            echo "$pid"
            return
        fi
        log_info_msg "Checking for consistent mysql PID: $pid."
    done
    echo "$pid"
}


log_info_msg "Bootstraping galera cluster."
# Get the myid of the galera node
if [ -e $MYIDFILE ]; then
    myid=$(cat $MYIDFILE)
    log_info_msg "Galera node ID: $myid"
else
    log_error_msg "Galera node ID not set in $MYIDFILE exiting bootstrap..."
    exit 0
fi


# Bootstrap galera cluster
retry_flag=0
bootstrap_retry_count=$(($RETRY_TIMEOUT / RETRY_INTERVAL))
for i in $(eval echo {1..$bootstrap_retry_count}); do
    mysql_pid=$(verify_mysql)
    if [ "$mysql_pid" == '' ]; then
        log_warn_msg "Mysql stopped, trying to start...."
        if [ $myid == 1 ]; then
            cmd="service mysql start --wsrep_cluster_address=gcomm://"
            log_info_msg "Starting mysql : $cmd"
            $cmd >> $LOGFILE
        else
            if [ $retry_flag == 1 ]; then
                cmd="rm /var/lib/mysql/grastate.dat"
                log_info_msg "Removing mysql grastate.dat file : $cmd"
                $cmd >> $LOGFILE
            fi
            cmd="service mysql start"
            log_info_msg "Starting mysql : $cmd"
            $cmd >> $LOGFILE
        fi
        retry_flag=1
        sleep 5
    else
        log_info_msg "Galera cluster is up and running."
        log_info_msg "Galera bootstrap completed."
        exit 0
    fi
done
log_error_msg "Galera bootstrap Failed."
