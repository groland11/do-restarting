![last commit](https://img.shields.io/github/last-commit/groland11/do-restarting.svg)
![release date](https://img.shields.io/github/release-date/groland11/do-restarting.svg)
![languages](https://img.shields.io/github/languages/top/groland11/do-restarting.svg)
![license](https://img.shields.io/github/license/groland11/do-restarting.svg)

# do-restarting
Similar to "needs-restarting" in Red Hat Enterprise Linux, do-restarting actually restarts the services that need to be restarted.
- Does not rely on "needs-restarting -s" as this does not seem to work reliably. Instead do-restarting provides its own mapping of process names to service names.
- Comprehensive debugging output. Debugging mode does not restart the services.
- Supports blacklisting and whitelisting of services in a configuration file

## Usage
```
./do-restarting.py -h
usage: do-restarting.py [-h] [-q] [-d] [-c CONFIGFILE] [-v] [-V]

Restart all services that need to be restarted

optional arguments:
  -h, --help            show this help message and exit
  -q, --quiet           only display error messages and certificate file names
  -d, --debug           generate additional debug information
  -c CONFIGFILE, --configfile CONFIGFILE
                        configuration file (default: /usr/local/etc/do-restarting.conf)
  -v, --verbose         increase output verbosity
  -V, --version         show program's version number and exit
```

## Example
