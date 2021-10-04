
import re
import os
import sys
import time
import tempfile
import subprocess


_pypi_project = "rezup-api"

_local_upgrade_source = os.getenv("REZUP_UPGRADE_SOURCE")

_pause_upgrade_period = int(os.getenv("REZUP_UPGRADE_PAUSE",
                                      86400))  # default to 1 day


def fetch_latest_version_from_local():
    src_ver = os.path.join(
        _local_upgrade_source, "src", "rezup", "_version.py"
    )

    g = {"__version__": None}
    with open(src_ver) as f:
        exec(f.read(), g)

    return g["__version__"]


def fetch_latest_version_from_pypi():
    import requests

    _pypi_url = "https://pypi.python.org/simple/{}".format(_pypi_project)
    _regex_version = re.compile(".*{}-(.*)\\.tar\\.gz".format(_pypi_project))

    try:
        response = requests.get(url=_pypi_url, timeout=1)
    except (requests.exceptions.Timeout, requests.exceptions.ProxyError):
        pass
    else:
        latest_str = ""
        for line in response.text.split():
            result = _regex_version.search(line)
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

    if time.time() - get_upgrade_check_time() < _pause_upgrade_period:
        return

    current = version.Version(__version__)
    latest_str = fetch_latest()
    latest = None
    try:
        latest = version.Version(latest_str)
    except (version.VersionError, TypeError):
        print("Failed to parse %s version: %s" % (_pypi_project, latest_str))

    log_upgrade_check_time()

    if not latest:
        print("Auto upgrade failed.")
        return

    if not latest > current:  # already latest
        return

    if latest.major > current.major:
        print("Major version bumped, not safe to upgrade automatically.")
        return

    print("Auto upgrading rezup (%s) .." % str(latest))
    upgrade()
    restart()


def upgrade():
    args = [
        sys.executable, "-m", "pip", "install", "-qq", "--upgrade",
        _local_upgrade_source or _pypi_project
    ]
    subprocess.check_call(args)


def restart():
    args = sys.argv[:]
    # ensure first argument is executable
    #   (could be __main__.py if rezup is called as module)
    if sys.argv[0].endswith("__main__.py"):
        args = [sys.executable, "-m", "rezup"] + args[1:]

    if sys.platform == "win32":
        sys.exit(
            subprocess.run(args).returncode
        )
    else:
        os.execv(args[0], args)


def update_record_file():
    return os.path.join(tempfile.gettempdir(), ".%s.txt" % _pypi_project)


def get_upgrade_check_time():
    timestamp = 0
    upgrade_record = update_record_file()

    if os.path.isfile(upgrade_record):

        with open(upgrade_record, "r") as record:
            line = record.read().strip()

        try:
            timestamp = float(line)
        except TypeError:
            pass

    return timestamp


def log_upgrade_check_time():
    timestamp = time.time()
    upgrade_record = update_record_file()

    with open(upgrade_record, "w") as record:
        record.write(str(timestamp))
