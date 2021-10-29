
import os
import sys
import fire
from . import get_rezup_version
from .container import Container, iter_containers


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
    """CLI entry point"""
    if len(sys.argv) == 1:  # for fast access
        sys.argv += ["use", Container.DEFAULT_NAME]

    patch_fire_help(my_order=[
        "use",
        "add",
        "drop",
        "status",
    ])
    fire.Fire(RezupCLI, name="rezup")


class RezupCLI:
    """Rez launching environment manager

                   * Run `rezup -` for COMMANDS help *
               * This CLI is powered by google/python-fire *

    A Rez production virtual environment management tool, which allows safe
    environment update without any interruption. Plus a convenient virtual
    environment setup interface.

    https://github.com/davidlatwe/rezup

    Args:
        version: Show current version and exit
        latest: Show latest version of rezup(api) in PyPI and exit.

    """
    def __init__(self, version=False, latest=False):
        if version:
            prompt_exit(get_rezup_version())
        if latest:
            prompt_exit(fetch_latest_version_from_pypi())

        disable_rezup_if_entered()

        self._job = None

    def _compose_job(self, do):
        """Compose the full job command from sys.argv

        For input like the example below, the full command cannot be parsed
        by fire due to the `-` in there. Hence this helper. Also, quoting
        is being handled as well. Experimentally..

            $ rezup use -do rez-env -- python -c "print('hello')"

        """
        self._job = do

        for flag in ["-d", "--do"]:
            if flag in sys.argv:
                index = sys.argv.index(flag) + 1

                args = []
                for a in sys.argv[index:]:
                    ra = repr(a)
                    args.append(
                        ra if "'" in a and not ra.startswith("'") else a
                    )

                self._job = " ".join(args)

    def use(self, name=Container.DEFAULT_NAME, do=None):
        """Step into a container. Run `rezup use -h` for help

        This will open a sub-shell which has Rez venv ready to use. Simply
        type 'exit' when finished.

        Usages:

            - for quick start, auto use default container '.main'
            $ rezup

            - use container 'foo'
            $ rezup use foo

            - use foo and do job (non-interactive session)
            $ rezup use foo --do {script.bat or "quoted command"}

        Args:
            name (str): container name
            do (str): run a shell script or command and exit

        """
        self._compose_job(do)

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
        """Add one container revision. Run `rezup add -h` for help

        This will create a new container revision (a new Rez venv setup) with
        corresponding recipe file.

        Usages:

            - create & use new rev from container '.main' (with ~/rezup.toml)
            $ rezup add

            - create & use new rev from container 'foo' (with ~/rezup.foo.toml)
            $ rezup add foo

            - create new rev from remote container
            $ rezup add --remote --skip-use

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
        """Remove a container. Run `rezup drop -h` for help

        Remove entire container from disk. This command isn't ready yet, use
        with caution.

        Usages:

            - remove container foo
            $ rezup drop foo

        Args:
            name (str): container name

        """
        container = Container(name)
        container.purge()

    def status(self, name=None):
        """Show status of containers. Run `rezup status -h` for help

        Displaying some useful info about current visible containers..

        Usages:

            - list containers and info
            $ rezup status

            - show detailed info of specific container
            $ rezup status foo

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


def patch_fire_help(my_order):
    """For patching COMMANDS order in Fire CLI help text

    When passing a class into Fire, COMMANDS that are showing in help-text
    are being sorted alphabetically. That's because the COMMANDS are listed
    by `inspect.getmembers` which will return member in sorted ordering.

    I'd like to maintain my own custom order, hence this patch.

    Links:
        https://github.com/google/python-fire/issues/298
        https://github.com/google/python-fire/pull/310

    Args:
        my_order (list): List of command names

    """
    from fire import completion

    _original = completion.VisibleMembers

    def VisibleMembers(*args, **kwargs):
        sorted_members = _original(*args, **kwargs)
        mapped_members = dict(sorted_members)
        sorted_names = [n for n, m in sorted_members]

        re_ordered = [
            (n, mapped_members[n]) for n in my_order if n in sorted_names
        ] + [
            (n, mapped_members[n]) for n in sorted_names if n not in my_order
        ]

        return re_ordered

    completion.VisibleMembers = VisibleMembers
