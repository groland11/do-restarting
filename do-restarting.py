#!/usr/bin/env python3
# Requires Python >= 3.6
import argparse
from configparser import ConfigParser,MissingSectionHeaderError
from datetime import datetime
import logging
import os
import re
import subprocess
import sys
from typing import Union

__license__ = "GPLv3"
__version__ = "0.9.0"

DEBUG = False

# Check for minimum Python version
if not sys.version_info >= (3, 6):
    print("ERROR: Requires Python 3.6 or higher")
    exit(1)

# Mapping between process and daemon
MAP = { "/usr/bin/python3 -s /usr/sbin/firewalld": "firewalld",
        "/usr/bin/dbus-daemon": "dbus",
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
        "/usr/sbin/syslog-ng": "syslog-ng",
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
        "/usr/sbin/clamd": "clamd@*",
        "/usr/bin/freshclam": "clamav-freshclam",
        "/usr/sbin/xinetd": "xinetd",
        "/usr/sbin/radiusd": "radiusd",
        "/usr/sbin/named": "named",
        "(sd-pam)": "", # https://bugzilla.redhat.com/show_bug.cgi?id=1070403
        "login ": "", # Mind the space at the end
        "/usr/libexec/pcp/bin/pmcd": "pmcd",
        "/usr/libexec/pcp/bin/pmlogger": "pmlogger",
        "/usr/libexec/pcp/bin/pmpause": "pmlogger",
        "/var/lib/pcp/": "pmcd",
        "/usr/sbin/nfsdcld": "nfsdcld",
        "/usr/local/qualys/cloud-agent/": "qualys-cloud-agent",
        "/opt/nessus_agent/sbin/": "nessusagent",
        "/usr/sbin/dhcpd": "dhcpd",
        "/usr/sbin/irqbalance": "irqbalance"
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


def read_config(file: Union[str, None]="") -> dict:
    """Read configuration file

    Global blacklist variable is updated to reflect blacklist and whitelist
    parameters in config file. Individual service configurations are
    returned in a dictionary.

    Args:
        file (str, None): Path of configuration file 

    Returns:
        Dictionary of parameters for individual services
    """

    global BLACKLIST
    logger = logging.getLogger(__name__)
    config_file = "/usr/local/etc/do-restarting.conf"
    config_lists = {"blacklist": [], "whitelist": []}
    services_config = {}

    if file is not None and os.path.isfile(file):
        config_file = file

    config_object = ConfigParser()

    # Read MAIN section
    config_object.read(config_file)
    for config_list in config_lists:
        try:
            userinfo = config_object["MAIN"]
            logger.debug(f"Using config file: {config_file}")
            config_lists[config_list] = [s.strip() for s in userinfo[config_list].split(",")]
        except KeyError as e:
            pass
        except MissingSectionHeaderError as e:
            logger.error(f"Invalid configuration file format ({config_file})")
        except:
            logger.error(f"Unable to parse configuration file {config_file}")

    # Merge config blacklist and whitelist into global BLACKLIST
    if len(config_lists["blacklist"]) > 0 or len(config_lists["whitelist"]) > 0:
        BLACKLIST.update(config_lists["blacklist"])
        BLACKLIST.difference_update(config_lists["whitelist"])
        logger.debug(f"Blacklist is {BLACKLIST}")

    # Read service sections
    for section in config_object.keys():
        if section in ["MAIN", "DEFAULT"]:
            continue
        logger.debug(f"Reading config section [{section}] ...")
        userinfo = config_object[section]
 
        # Searching vor config parameters: "dow", "hours", "pre", "post"
        params = {"dow": "", "hours": "", "pre": "", "post": ""}
        for param in params:
            try:
                params[param] = [s.strip() for s in userinfo[param].split(",")]
            except:
                pass

        logger.debug(f"{params}")
        services_config[section] = params

    return services_config


def check_dow(dow: int, dow_range: list) -> bool:
    """Check if weekday falls into a given range

    Args:
        dow (int): Date of week as number (0=mon, ..., 6=sun)
        dow_range (list): Range of weekdays, days are specified in short notation:
                      mon,tue,wed,thu,fri,sat,sun
                      List entries may be single values or ranges.
                      Example:
                      ['mon', 'wed-fri', 'sun']

    Returns:
        True: Date of week is within range
        False: Date of week is not within range

    Throws:
        ValueError: Invalid values given in parameter dow_range
    """

    dows = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    conf_dow = []

    for value in dow_range:
        for i in dows:
            value = value.replace(i, str(dows.index(i))) 

        # Check if dow contains a range and expand it to single values
        pos = value.find("-")
        if pos >= 0:
            start = value[:pos]
            end = value[pos + 1:]
            conf_dow.extend(list(range(int(start), int(end) + 1)))
        else:
            conf_dow.append(int(value))

    if len(conf_dow) > 0 and dow in conf_dow:
        return True

    return False


def check_hour(hour: int, hour_range: list) -> bool:
    """Check if hour falls into a given range

    Args:
        hour (int): Hour to check (24h format)
        hour_range (list): Range of hours as strings
                      List entries may be single values or ranges.
                      Example:
                      ['6-8', '12', '20']

    Returns:
        True: Hour is within range
        False: Hour is not within range

    Throws:
        ValueError: Invalid values given in parameter hour_range
    """

    conf_hours = []

    for value in hour_range:
        # Check if hours contains a range
        pos = value.find("-")
        if pos >= 0:
            start = value[:pos]
            end = value[pos + 1:]
            conf_hours.extend(list(range(int(start), int(end) + 1)))
        else:
            conf_hours.append(int(value))

    if len(conf_hours) > 0 and hour in conf_hours:
        return True

    return False


def restart(daemon: str, config: Union[dict, None]) -> bool:
    """Restart daemon / service

    Service will not be restarted in debug mode.

    Args:
        daemon (str): Name of service to restart
        config (dict): Configuration for service

    Returns:
        True: Service has been restarted successfully
        False: Error occurred while restarting service.
               This could be due to a failed precondition or an error
               with systemctl. Details about the error will be logged.
    """

    global DEBUG
    logger = logging.getLogger(__name__)
    ret = True

    # Check if there is a configuration for this service
    if config is not None:
        # Check day of week
        if len(config.get("dow")) > 0:
            logger.debug(f"Date of week configured for service {daemon}: {sorted(config.get('dow'))}")
            cur_dow = datetime.today().weekday()
            try:
                if not check_dow(cur_dow, config.get("dow")):
                    logger.info(f"Skipping restart of {daemon} because current day of week {cur_dow} is not configured in {config['dow']})")
                    return True
                else:
                    logger.info(f"{daemon} configured for restart in {config['dow']})")
            except ValueError:
                logger.warning(f"Invalid value in day of week parameter for service {daemon} ({config['dow']})")

        # Check hour
        if len(config.get("hours")) > 0:
            logger.debug(f"Hours configured for service {daemon}: {sorted(config.get('hours'))}")
            cur_hour = datetime.now().hour
            try:
                if not check_hour(cur_hour, config.get("hours")):
                    logger.info(f"Skipping restart of {daemon} because current hour {cur_hour} is not configured in {config['hours']})")
                    return True
                else:
                    logger.info(f"{daemon} configured for restart in {config['hours']})")
            except ValueError:
                logger.warning(f"Invalid value in hours parameter for service {daemon} ({config['hours']})")

        # Run pre command
        if len(config.get("pre")) > 0:
            cmd = config["pre"][0].strip()
            logger.debug(f"Running pre command {cmd} ...")
            try:
                output = subprocess.run(cmd, timeout=60, encoding="utf-8", check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.TimeoutExpired as e:
                logger.error("Failed to restart {daemon}: pre command timeout expired ({e})")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restart {daemon}: pre command returned: {e}")
                return False
            else:
                logger.info(f"{daemon} pre command executed successfully ({cmd})")

    # Restart service
    try:
        logger.debug(f"Restarting {daemon} ...")
        if not DEBUG:
            output = subprocess.run(["systemctl", "restart", daemon], timeout=60, check=True)
    except FileNotFoundError as e:
        logger.error("Failed to restart {daemon} (systemctl not found)")
        ret = False
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to restart {daemon} (systemctl returned {e.returncode})")
        ret = False
    else:
        logger.info(f"Successfully restarted {daemon}")

    # Run post command if configured
    if config is not None and len(config.get("post")) > 0:
        cmd = config["post"][0].strip()
        logger.debug(f"Running post command {cmd} ...")
        try:
            output = subprocess.run(cmd, timeout=60, encoding="utf-8", check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.TimeoutExpired as e:
            logger.error("post command timeout expired ({e})")
        except subprocess.CalledProcessError as e:
            logger.error(f"post command returned: {e}")
        else:
            logger.info(f"{daemon} post command executed successfully ({cmd})")

    return ret


def get_daemons() -> set:
    """Retrieve list of daemons / services that need to be restarted

    Returns:
        Set of services that need to be restarted. Service names do not
        contain the trailing ".service".

    Throws:
        Exception: needs-restarting returned an error
    """

    global BLACKLIST
    logger = logging.getLogger(__name__)
    daemons = set()

    try:
        output = subprocess.run(["needs-restarting"], timeout=30, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        logger.error("needs-restarting not found")
        raise Exception
    except subprocess.TimeoutExpired as e:
        logger.error("needs-restarting timeout expired ({e})")
        raise Exception
    else:
        if output.returncode != 0:
            logger.error(f"needs-restarting returned {output.returncode}: {output.stderr.strip()}")
            raise Exception
        else:
            for line in output.stdout.splitlines():
                try:
                    cmd = line.split(":")[1].strip()
                except IndexError as e:
                    logger.debug(f"Skipping output line '{line}'")
                else:
                    for process in MAP:
                        if cmd.startswith(process):
                            daemon = MAP[process]
                            daemons.add(daemon) if daemon not in BLACKLIST and daemon != "" else logger.debug(f"Skipping {cmd} ({daemon if daemon != '' else '<no daemon process>'})")
                            break
                    else:
                        logger.debug(f"Unknown process {cmd}")

    return daemons


def main():
    ''' Main function'''
    global DEBUG

    # Read commandline arguments
    args = parseargs()
    if args.debug:
        DEBUG = True

    # Start logging
    logger = get_logger(args.debug)
    logger.debug("Running in debug mode. Processes will not be restarted!")

    # Check for configuration file
    services_config = read_config(args.configfile)

    # Restart daemons
    try:
        daemons = get_daemons()
    except:
        exit(1)
    else:
        for daemon in daemons:
            restart(daemon, services_config.get(daemon))


if __name__ == "__main__":
    main()
