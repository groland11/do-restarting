#!/usr/bin/env python3
import argparse
from configparser import ConfigParser,MissingSectionHeaderError
import logging
import os
import re
import subprocess
import sys
from typing import Union


DEBUG = False

# Mapping between process and daemon
MAP = { "/usr/bin/python3 -s /usr/sbin/firewalld": "firewalld",
        "/usr/bin/dbus-broker": "dbus",
        "dbus-broker": "dbus",
        "/usr/lib/polkit-1/polkitd": "polkit",
        "/usr/sbin/atd": "atd",
        "/usr/sbin/smartd": "smartd",
        "/usr/sbin/httpd": "httpd",
        "/usr/libexec/mysqld": "mysqld",
        "/usr/libexec/platform-python /usr/libexec/rhsm-service": "rhsm",
        "/usr/sbin/wpa_supplicant": "wpa_supplicant",
        "/usr/libexec/upowerd": "upower",
        "/usr/libexec/accounts-daemon": "accounts-daemon",
        "/usr/libexec/packagekitd": "packagekit",
        "/usr/sbin/keepalived": "keepalived",
        "/usr/sbin/lvmetad": "",
        "/sbin/rpcbind": "rpcbind",
        "/usr/bin/rpcbind": "rpcbind",
        "/usr/sbin/rpc.statd": "rpc-statd",
	"/usr/sbin/rpc.mountd": "nfs-mountd",
	"/usr/sbin/nfsdcld": "nfsdcld",
        "/usr/sbin/sedispatch": "",
        "/sbin/auditd": "auditd",
        "/usr/libexec/postfix/master": "postfix",
        "/usr/sbin/rsyslogd": "rsyslog",
        "/usr/sbin/xrdp": "xrdp",
        "qmgr": "postfix",
        "tlsmgr": "postfix",
        "/usr/libexec/postfix/master": "postfix",
        "/usr/libexec/platform-python -Es /usr/sbin/tuned": "tuned",
        "/usr/bin/python3 -Es /usr/sbin/tuned": "tuned",
        "/opt/puppetlabs/puppet/bin/ruby /opt/puppetlabs/puppet/bin/puppet": "puppet",
        "/usr/sbin/sshd": "sshd",
        "sshd": "",
        "/usr/sbin/NetworkManager": "NetworkManager",
        "/usr/sbin/sssd": "sssd",
        "/usr/libexec/sssd/sssd_ssh": "sssd",
        "/usr/libexec/sssd/sssd_pam": "sssd",
        "/usr/libexec/sssd/sssd_nss": "sssd",
        "/usr/libexec/sssd/sssd_be": "sssd",
        "/usr/libexec/platform-python -s /usr/sbin/firewalld": "firewalld",
        "/usr/bin/python2 -Es /usr/sbin/firewalld": "firewalld",
        "/opt/bacula/bin/bacula-fd": "bacula-fd",
        "/usr/sbin/chronyd": "chronyd",
        "/sbin/auditd": "auditd",
        "/usr/lib/systemd/systemd ": "systemd", # Mind the space at the end
        "/usr/lib/systemd/systemd-udevd": "systemd-udevd",
        "/usr/lib/systemd/systemd-journald": "systemd-journald",
        "/usr/lib/systemd/systemd-logind":  "systemd-logind",
        "/usr/lib/systemd/systemd-machined": "systemd-machined",
        "/usr/lib/systemd/systemd  --switched-root": "systemd",
        "/usr/lib/systemd/systemd --system": "systemd",
        "/usr/bin/rhsmcertd": "rhsmcertd",
        "/usr/bin/freshclam": "clamav-freshclam",
        "/usr/sbin/xinetd": "xinetd",
        "/usr/sbin/radiusd": "radiusd",
        "(sd-pam)": "", # https://bugzilla.redhat.com/show_bug.cgi?id=1070403
        "login ": "", # Mind the space at the end
        "/usr/libexec/pcp/bin/pmcd": "pmcd",
        "/usr/libexec/pcp/bin/pmlogger": "pmlogger",
        "/usr/libexec/pcp/bin/pmpause": "pmlogger",
        "/var/lib/pcp/": "pmcd",
	"/usr/sbin/nfsdcld": "nfsdcld",
	"/usr/local/qualys/cloud-agent/": "qualys-cloud-agent",
	"/usr/sbin/dhcpd": "dhcpd"
}


# Daemons that must not be restarted
BLACKLIST = {
        "dbus",
        "systemd",
        "auditd",
        "mysqld",
        "httpd",
        "bacula-sd",
        "bacula-dir",
        "keepalived",
	"nfs-server",
	"nfsdcld",
	"rpc-statd",
	"nfs-mountd"
}


class LogFilter(logging.Filter):
    def filter(self, record):
        return record.levelno in (logging.DEBUG, logging.WARNING, logging.INFO)


def parseargs():
    """Process command line arguments"""
    parser = argparse.ArgumentParser(description="Restart all services that need to be restarted")
    parser.add_argument("-d", "--debug", action="store_true",
        help="generate additional debug information")
    parser.add_argument("-c", "--configfile", action="store",
        help="configuration file (default: /usr/local/etc/do-restarting.conf)")
    parser.add_argument("-V", "--version", action="version", version="1.0.0")
    return parser.parse_args()


def get_logger(debug: bool = False) -> logging.Logger:
    """Retrieve logging object"""
    logger = logging.getLogger(__name__)

    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    h1.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)-8s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    h1.addFilter(LogFilter())

    h2 = logging.StreamHandler(sys.stdout)
    h2.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)-8s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    h2.setLevel(logging.ERROR)

    logger.addHandler(h1)
    logger.addHandler(h2)

    return logger


def read_config(file: Union[str, None]=""):
    """Read configuration file"""
    global BLACKLIST
    logger = logging.getLogger(__name__)
    config_file = "/usr/local/etc/do-restarting.conf"
    blacklist = []
    whitelist = []

    if file is not None and os.path.isfile(file):
        config_file = file

    config_object = ConfigParser()

    try:
        config_object.read(config_file)
        userinfo = config_object["MAIN"]
        logger.debug(f"Using config file: {config_file}")
        blacklist = [ s.strip() for s in userinfo["blacklist"].split(",")]
        whitelist = [ s.strip() for s in userinfo["whitelist"].split(",")]
    except KeyError as e:
        pass
    except MissingSectionHeaderError as e:
        logger.error(f"Invalid configuration file format ({config_file})")
    except:
        logger.error(f"Unable to parse configuration file {config_file}")

    if len(blacklist) > 0 or len(whitelist) > 0:
        BLACKLIST.update(blacklist)
        BLACKLIST.difference_update(whitelist)
        logger.debug(f"Blacklist is {BLACKLIST}")


def restart(daemon: str) -> bool:
    """
    Restart daemon / service
    :param daemon:
    :return:
    """
    global DEBUG
    logger = logging.getLogger(__name__)
    ret = True

    try:
        logger.debug(f"Restarting {daemon} ...")
        if not DEBUG:
            output = subprocess.run(["systemctl", "restart", daemon], timeout=10, check=True)
    except FileNotFoundError as e:
        logger.error("systemctl not found")
        ret = False
    except subprocess.CalledProcessError as e:
        logger.error(f"systemctl returned {e.returncode}")
        ret = False

    return ret


def get_daemons() -> set:
    """
    Retrieve list of daemons / services that need to be restarted
    :return:
    """
    global BLACKLIST
    logger = logging.getLogger(__name__)
    daemons = set()

    try:
        output = subprocess.run(["needs-restarting"], timeout=10, encoding="utf-8", check=True, capture_output=True)
    except FileNotFoundError as e:
        logger.error("needs-restarting not found")
    except subprocess.CalledProcessError as e:
        logger.error(f"needs-restarting returned {e.returncode}")
    else:
    	for line in output.stdout.splitlines():
            found = False
            cmd = line.split(":")
            if len(cmd) > 1:
                for process in MAP:
                    if cmd[1].strip().startswith(process):
                        daemon = MAP[process]
                        daemons.add(daemon) if daemon not in BLACKLIST and daemon != "" else logger.debug(f"Skipping {cmd[1].strip()} ({daemon if daemon != '' else '<no daemon process>'})")
                        found = True
                        break
                if not found:
                    logger.debug(f"Unknown process {cmd[1].strip()}")

    return daemons


def main():
    global DEBUG

    args = parseargs()
    if args.debug:
        DEBUG = True
    logger = get_logger(args.debug)
    read_config(args.configfile)

    daemons = get_daemons()
    for daemon in daemons:
        if restart(daemon):
            logger.info(f"Successfully restarted {daemon}")
        else:
            logger.error(f"Failed to restart {daemon}")


if __name__ == "__main__":
    main()
