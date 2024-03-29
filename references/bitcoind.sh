#
# Install bitcoind
#
aptitude install -y python-software-properties
add-apt-repository -y ppa:bitcoin/bitcoin
aptitude update
aptitude -y upgrade
aptitude install -y bitcoind

#
# Create bitcoin user
#
useradd --system bitcoin
mkdir -p /home/bitcoin/.bitcoin/

#
# Write configuration files
#
tee /home/bitcoin/.bitcoin/bitcoin.conf << EOF
testnet=0
server=1
daemon=1
gen=0
rpcuser=yellowcoin
rpcpassword=kyqDyBc3w2yaAgrEBTCVFAUPBYGALzLn3fZNQxwPMQWUZyhMvrgU4nT4vGmsVYTk
rpcallowip=*.*.*.*
rpcport=8332
rpctimeout=30
EOF

tee /etc/init.d/bitcoind << EOF
#! /bin/sh
### BEGIN INIT INFO
# Provides:          bitcoind
# Required-Start:    \$remote_fs
# Required-Stop:     \$remote_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: bitcoind daemon startup script
# Description:       bitcoind daemon startup script
### END INIT INFO

# Author: Pavel A. Karoukin <pavel@yepcorp.com>
#

# Do NOT "set -e"

# PATH should only include /usr/* if it runs after the mountnfs.sh script
PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="bitcoind"
NAME=bitcoind
DAEMON=/usr/bin/\$NAME
PIDFILE=/var/run/\$NAME.pid
SCRIPTNAME=/etc/init.d/\$NAME
CHUID=bitcoin:bitcoin

# Exit if the package is not installed
[ -x "\$DAEMON" ] || exit 0

# Read configuration variable file if it is present
[ -r /etc/default/\$NAME ] && . /etc/default/\$NAME

# Load the VERBOSE setting and other rcS variables
. /lib/init/vars.sh

# Define LSB log_* functions.
# Depend on lsb-base (>= 3.0-6) to ensure that this file is present.
. /lib/lsb/init-functions

#
# Function that starts the daemon/service
#
do_start()
{
   # Return
   #   0 if daemon has been started
   #   1 if daemon was already running
   #   2 if daemon could not be started
   start-stop-daemon --start --quiet --pidfile \$PIDFILE --exec \$DAEMON --test > /dev/null \
      || return 1
   start-stop-daemon --start --quiet --chuid \$CHUID --pidfile \$PIDFILE --exec \$DAEMON -- \
      \$DAEMON_ARGS \
      || return 2
}

#
# Function that stops the daemon/service
#
do_stop()
{
   # Return
   #   0 if daemon has been stopped
   #   1 if daemon was already stopped
   #   2 if daemon could not be stopped
   #   other if a failure occurred
   \$DAEMON stop
   start-stop-daemon --stop --quiet --retry=TERM/30/KILL/5 --pidfile \$PIDFILE --name \$NAME
   RETVAL="\$?"
   [ "\$RETVAL" = 2 ] && return 2
   # Wait for children to finish too if this is a daemon that forks
   # and if the daemon is only ever run from this initscript.
   # If the above conditions are not satisfied then add some other code
   # that waits for the process to drop all resources that could be
   # needed by services started subsequently.  A last resort is to
   # sleep for some time.
   start-stop-daemon --stop --quiet --oknodo --retry=0/30/KILL/5 --exec \$DAEMON
   [ "\$?" = 2 ] && return 2
   # Many daemons don't delete their pidfiles when they exit.
   rm -f \$PIDFILE
   return "\$RETVAL"
}

#
# Function that sends a SIGHUP to the daemon/service
#
do_reload() {
   #
   # If the daemon can reload its configuration without
   # restarting (for example, when it is sent a SIGHUP),
   # then implement that here.
   #
   start-stop-daemon --stop --signal 1 --quiet --pidfile \$PIDFILE --name \$NAME
   return 0
}

case "\$1" in
  start)
   [ "\$VERBOSE" != no ] && log_daemon_msg "Starting \$DESC" "\$NAME"
   do_start
   case "\$?" in
      0|1) [ "\$VERBOSE" != no ] && log_end_msg 0 ;;
      2) [ "\$VERBOSE" != no ] && log_end_msg 1 ;;
   esac
   ;;
  stop)
   [ "\$VERBOSE" != no ] && log_daemon_msg "Stopping \$DESC" "\$NAME"
   do_stop
   case "\$?" in
      0|1) [ "\$VERBOSE" != no ] && log_end_msg 0 ;;
      2) [ "\$VERBOSE" != no ] && log_end_msg 1 ;;
   esac
   ;;
  #reload|force-reload)
   #
   # If do_reload() is not implemented then leave this commented out
   # and leave 'force-reload' as an alias for 'restart'.
   #
   #log_daemon_msg "Reloading \$DESC" "\$NAME"
   #do_reload
   #log_end_msg \$?
   #;;
  restart|force-reload)
   #
   # If the "reload" option is implemented then remove the
   # 'force-reload' alias
   #
   log_daemon_msg "Restarting \$DESC" "\$NAME"
   do_stop
   case "\$?" in
     0|1)
      do_start
      case "\$?" in
         0) log_end_msg 0 ;;
         1) log_end_msg 1 ;; # Old process is still running
         *) log_end_msg 1 ;; # Failed to start
      esac
      ;;
     *)
        # Failed to stop
      log_end_msg 1
      ;;
   esac
   ;;
  *)
   #echo "Usage: \$SCRIPTNAME {start|stop|restart|reload|force-reload}" >&2
   echo "Usage: \$SCRIPTNAME {start|stop|restart|force-reload}" >&2
   exit 3
   ;;
esac

:
EOF


#
# Set permissions
#
chmod +x /etc/init.d/bitcoind
chmod 400 /home/bitcoin/.bitcoin/bitcoin.conf
chown -R bitcoin:bitcoin /home/bitcoin/.bitcoin/

#
# Update rc.d
#
update-rc.d bitcoind defaults

#
# Start the server
#
/etc/init.d/bitcoind start

