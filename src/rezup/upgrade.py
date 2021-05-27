
import re
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime


_pypi_project = "rezup-api"

_local_upgrade_source = os.getenv("REZUP_UPGRADE_SOURCE")

_upgrade_record = Path(tempfile.gettempdir()) / (".%s.txt" % _pypi_project)

_pause_upgrade_period = int(os.getenv("REZUP_UPGRADE_PAUSE",
                                      86400))  # default to 1 day


def fetch_latest_version_from_local():
    src_ver = Path(_local_upgrade_source) / "src" / "rezup" / "_version.py"

    g = {"__version__": None}
    with open(src_ver) as f:
        exec(f.read(), g)

    return g["__version__"]


_pypi_url = "https://pypi.python.org/simple/{}".format(_pypi_project)
_regex_pypi_version = re.compile(".*{}-(.*)\\.tar\\.gz".format(_pypi_project))


def fetch_latest_version_from_pypi():
    import requests

    try:
        response = requests.get(url=_pypi_url, timeout=1)
    except (requests.exceptions.Timeout, requests.exceptions.ProxyError):
        pass
    else:
        latest_str = ""
        for line in response.text.split():
            result = _regex_pypi_version.search(line)
            if result:
                latest_str = result.group(1)

        if latest_str:
            return latest_str

    print("Failed to fetch latest %s version from PyPi.." % _pypi_project)


def show_latest():
    source = "local" if _local_upgrade_source else "PyPI"
    print("Latest from %s: %s" % (source, fetch_latest()))


def fetch_latest():
    if _local_upgrade_source:
        return fetch_latest_version_from_local()
    else:
        return fetch_latest_version_from_pypi()


def auto_upgrade():
    from ._vendor import version
    from ._version import __version__

    if datetime.now().timestamp() - get_last_upgrade_time() \
            < _pause_upgrade_period:
        return

    current = version.Version(__version__)
    latest_str = fetch_latest()
    try:
        latest = version.Version(latest_str)
    except version.VersionError:
        print("Failed to parse %s version: %s" % (_pypi_project, latest_str))
        latest = None

    if not latest or not latest > current:
        return

    if latest.major > current.major:
        print("Major version bumped, not safe to upgrade automatically.")
        return

    # upgrade
    #
    args = [
        sys.executable, "-m", "pip", "install", "--upgrade",
        _local_upgrade_source or _pypi_project
    ]
    subprocess.check_call(args)

    # log
    #
    log_last_upgrade_time(datetime.now().timestamp())

    # restart
    #
    os.execv(sys.executable, sys.argv)


def get_last_upgrade_time():
    timestamp = datetime.now().timestamp()

    if _upgrade_record.is_file():

        with open(_upgrade_record, "r") as record:
            line = record.read().strip()

        try:
            timestamp = float(line)
        except TypeError:
            pass

    return timestamp


def log_last_upgrade_time(timestamp):
    with open(_upgrade_record, "w") as record:
        record.write(str(timestamp))