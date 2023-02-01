![last commit](https://img.shields.io/github/last-commit/groland11/do-restarting.svg)
![release date](https://img.shields.io/github/release-date/groland11/do-restarting.svg)
![languages](https://img.shields.io/github/languages/top/groland11/do-restarting.svg)
![license](https://img.shields.io/github/license/groland11/do-restarting.svg)

# do-restarting
Similar to "needs-restarting" in Red Hat Enterprise Linux, do-restarting actually restarts the services that need to be restarted.
- Does not rely on "needs-restarting -s" as this does not seem to work reliably. Instead do-restarting provides its own mapping of process names to service names.
- Comprehensive debugging output. Debugging mode does not restart the services.
- Supports blacklisting and whitelisting of services in configuration file
- Individual configuration for each service: Day of week and hours allowed for restart, pre- and post-command

## Requirements
- Red Hat Enterprise Linux 7/8/9
- Python >= 3.6
- Package "yum-utils" (needs-restarting)

## Usage
```
./do-restarting.py -h
usage: do-restarting.py [-h] [-d] [-c CONFIGFILE] [-V]

Restart all services that need to be restarted

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           generate additional debug information
  -c CONFIGFILE, --configfile CONFIGFILE
                        configuration file (default: /usr/local/etc/do-restarting.conf)
  -V, --version         show program's version number and exit
```

## Example
```
# ./do-restarting.py -c ./do-restarting.conf -d
2022-11-18 00:35:55 DEBUG   : Running in debug mode. Processes will not be restarted!
2022-11-18 00:35:55 DEBUG   : Using config file: ./do-restarting.conf
2022-11-18 00:35:55 DEBUG   : Using config file: ./do-restarting.conf
2022-11-18 00:35:55 DEBUG   : Blacklist is {'keepalived', 'httpd', 'systemd', 'nfsdcld', 'nfs-server', 'rpc-statd', 'auditd', 'nfs-mountd', 'bacula-sd', 'mysqld', 'bacula-dir'}
2022-11-18 00:35:55 DEBUG   : Reading config section [httpd] ...
2022-11-18 00:35:55 DEBUG   : {'dow': ['sat', 'sun'], 'hours': ['12-20', '15'], 'pre': ['"apachectl configtest"'], 'post': ['"systemctl status httpd"']}
2022-11-18 00:35:55 DEBUG   : Reading config section [firewalld] ...
2022-11-18 00:35:55 DEBUG   : {'dow': ['mon-fri'], 'hours': ['0-6', '12', '19'], 'pre': '', 'post': ''}
2022-11-18 00:35:57 DEBUG   : Skipping output line 'Updating Subscription Management repositories.'
2022-11-18 00:35:57 DEBUG   : Skipping /usr/lib/systemd/systemd rhgb --system --deserialize 38 (systemd)
2022-11-18 00:35:57 DEBUG   : Skipping /sbin/auditd (auditd)
2022-11-18 00:35:57 DEBUG   : Unknown process /sbin/agetty -o -p -- \u --noclear - linux
2022-11-18 00:35:57 DEBUG   : Skipping sshd (<no daemon process>)
2022-11-18 00:35:57 DEBUG   : Skipping /usr/lib/systemd/systemd --user (systemd)
2022-11-18 00:35:57 DEBUG   : Skipping (sd-pam) (<no daemon process>)
2022-11-18 00:35:57 DEBUG   : Skipping sshd (<no daemon process>)
2022-11-18 00:35:57 DEBUG   : Unknown process -bash
2022-11-18 00:35:57 DEBUG   : Unknown process /usr/bin/qemu-ga --method=virtio-serial --path=/dev/virtio-ports/org.qemu.guest_agent.0 --blacklist=guest-file-open,guest-file-close,guest-file-read,guest-file-write,guest-file-seek,guest-file-flush,guest-exec,guest-exec-status -F/etc/qemu-ga/fsfreeze-hook
2022-11-18 00:35:57 DEBUG   : Restarting dbus ...
2022-11-18 00:35:57 INFO    : Successfully restarted dbus
2022-11-18 00:35:57 DEBUG   : Restarting polkit ...
2022-11-18 00:35:57 INFO    : Successfully restarted polkit
2022-11-18 00:35:57 DEBUG   : Restarting systemd-logind ...
2022-11-18 00:35:57 INFO    : Successfully restarted systemd-logind
2022-11-18 00:35:57 DEBUG   : Restarting NetworkManager ...
2022-11-18 00:35:57 INFO    : Successfully restarted NetworkManager
```

## Sample configuration file
```
### Main section applies to all services
# Following configuration values are supported:
# blacklist: List of services that will not be restarted.
#     Service names must not include the trailing ".service".
#     Example: blacklist=httpd,myslqd,firewalld
# whitelist: List of services that will be restarted even though
#     they are hardcoded in the internal blacklist in the script.
#     Service names must not include the trailing ".service".
#     Example: whitelist=dbus
[MAIN]
blacklist=mysqld
whitelist=dbus,httpd,firewalld

### Sections for individual services
# Following configuration values are supported:
# dow: Day of week when service will be restarted
#      Valid values are "mon","tue","wed","thu","fri","sat","sun"
#      as a comma separated list or ranges of values.
#      Example: dow=mon-wed,fri
# hours: Hours when service will be restarted. If script is called
#      outside of the specified hours, restart of service will be 
#      skipped.
#      Example: hours=12-14,18-20
# pre: Pre condition to check before service will be restarted.
#      This can be any command that will be run in a shell as 
#      the calling user. If the return value is not zero, the 
#      service will not be restarted.
#      Example: pre="apachectl configtest"
# post: Post condition to check after service restart. If the
#      return value is not zero. an error message will be 
#      printed to stderr. This can be useful if the output
#      of the script is redirected to a log file that is 
#      monitored.
[httpd]
dow=sat,sun
hours=12-20,15
pre="apachectl configtest"
post="systemctl status httpd"

[firewalld]
dow=mon-fri
hours=0-6,12,19
```
