
import os
import sys
import fire
from .container import Container, iter_containers


def version_str():
    import rezup._version
    return "{name} {ver} from {lib} (python {x}.{y})".format(
        name="rezup",
        ver=rezup._version.__version__,
        lib=rezup.__path__[0],
        x=sys.version_info.major,
        y=sys.version_info.minor,
    )


def disable_rezup_if_entered():
    _con = os.getenv("REZUP_CONTAINER")
    if _con:
        print("Not allowed inside container, please exit first. "
              "(current: %s)" % _con)
        sys.exit(1)


def prompt_exit(message):
    print(message)
    sys.exit(0)


def run():
    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", Container.DEFAULT_NAME]

    fire.Fire(RezupCLI, name="rezup")


class RezupCLI:
    """Rez launching environment manager command line interface

    Args:
        version: show version and exit.
        check_latest: show version of latest rezup(api) and exit.

    """
    def __init__(self, version=False, check_latest=False):
        if version:
            prompt_exit(self.version)
        if check_latest:
            prompt_exit(self.latest)

        disable_rezup_if_entered()

        self._job = None

    @property
    def version(self):
        """show version and exit"""
        return version_str()

    @property
    def latest(self):
        """show latest version of rezup(api) from PyPI and exit"""
        return fetch_latest_version_from_pypi()

    def use(self, name=Container.DEFAULT_NAME, do=None):
        """Use container

        Args:
            name (str): container name
            do (str): run a shell script or command and exit

        """
        self._job = do

        container = Container(name)
        revision = container.get_latest_revision()

        if revision:
            sys.exit(
                revision.use(run_script=self._job)
            )
        else:
            if container.is_exists():
                print("Container '%s' exists but has no valid revision: %s"
                      % (container.name(), container.path()))
                sys.exit(1)

            else:
                # for quick first run
                print("Creating container automatically for first run..")
                self.add(name)

    def add(self, name=Container.DEFAULT_NAME, remote=False, skip_use=False):
        """Add container revision

        Args:
            name (str): container name
            remote (bool): add a remote revision
            skip_use (bool): add revision and exit

        """
        if remote:
            print("Creating remote container..")
            container = Container.create(name)
            if not container.is_remote():
                print("Remote root is not set.")
                sys.exit(1)
        else:
            print("Creating local container..")
            container = Container.create(name, force_local=True)

        revision = container.new_revision()

        if not skip_use:
            sys.exit(
                revision.use(run_script=self._job)
            )

    def drop(self, name):
        """Remove container

        Args:
            name (str): container name

        """
        container = Container(name)
        container.purge()

    def status(self, name=None):
        """Show status of containers

        Args:
            name (str): show status of specific container if name given

        """
        print("   Name   | Is Remote | Rev Count | Root     ")
        print("---------------------------------------------")
        status_line = "{name: ^10} {remote: ^11} {rev_count: ^11} {root}"

        for con in iter_containers():
            status = {
                "name": con.name(),
                "remote": "O" if con.is_remote() else "-",
                "rev_count": len(list(con.iter_revision())),
                "root": con.root(),
            }
            print(status_line.format(**status))

        if name:
            print("")
            local_con = Container(name, force_local=True)
            if local_con is not None:
                libs = local_con.libs()
                if libs.is_dir():
                    print("  Shared libs:")
                    for lib_name in local_con.libs().iterdir():
                        print("    %s" % lib_name)


def fetch_latest_version_from_pypi():
    import re

    try:
        from urllib.request import urlopen  # noqa, py3
    except ImportError:
        from urllib import urlopen    # noqa, py2

    name = "rezup-api"

    _pypi_url = "https://pypi.python.org/simple/{}".format(name)
    _regex_version = re.compile(".*{}-(.*)\\.tar\\.gz".format(name))

    f = urlopen(_pypi_url)
    text = f.read().decode("utf-8")
    f.close()

    latest_str = ""
    for line in text.split():
        result = _regex_version.search(line)
        if result:
            latest_str = result.group(1)

    if latest_str:
        return latest_str

    return "Failed to fetch latest %s version from PyPI.." % name
