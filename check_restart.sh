#!/bin/bash
# Check which services need restarting
# Services that must not be restarted are blacklisted

set +H

CHECKRESTART=needs-restarting
SERVICES=
RES=0
MSG=""
BLACKLIST=(
	"auditd.service"
	"dbus.service"
	"dbus-broker.service"
	"sshd.service"
	"user@[0-9]\+.service"
	"nfs-server.service"
	"nfs-mountd.service"
	"nfsdcld.service"
	"rpc-statd.service"
)

if (( $# != 0 )) ; then
    echo "Usage: ./check_restart.sh"
    exit 3
fi

SERVICES=$($CHECKRESTART -s 2>/dev/null | grep -v Updating | tr "\n" ";")
for s in ${BLACKLIST[@]}; do
	SERVICES=$(/bin/echo "${SERVICES}" | /bin/sed "s/${s};//g")
done
if [ -n "$SERVICES" ] ; then
        RES=2
        MSG="Services need restarting:$SERVICES"
fi

$($CHECKRESTART -r 1>/dev/null)
if [ $? -ne 0 ] ; then
        MSG="Server needs reboot;$MSG"
fi

case ${RES} in
    0)
        echo "OK - $MSG"
        exit 0
        ;;
    1)
        echo "CRITICAL - $MSG"
        exit 2
        ;;
    2)
        echo "WARNING - $MSG"
        exit 1
        ;;
    *)
        echo "CRITICAL - undefined error"
        exit 2
        ;;
esac

exit 3

