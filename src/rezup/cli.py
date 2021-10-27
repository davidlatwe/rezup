
import os
import sys
import argparse
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


def setup_parser():
    _con_def = Container.DEFAULT_NAME

    parser = argparse.ArgumentParser("rezup")
    parser.add_argument("-V", "--version", action="version",
                        help="show version and exit.",
                        version=version_str())
    parser.add_argument("-L", "--check-latest", action=VersionFromPyPI,
                        help="show version of latest rezup(api) and exit.")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    # cmd: use
    #
    parser_use = subparsers.add_parser("use", help="use container")
    parser_use.add_argument("name", nargs="?", default=_con_def,
                            help="container name. default: '%s'" % _con_def)
    parser_use.add_argument("-d", "--do",
                            help="run a shell script or command and exit.")

    # cmd: add
    #
    parser_add = subparsers.add_parser("add", help="add container revision")
    parser_add.add_argument("name", nargs="?", default=_con_def,
                            help="container name. default: '%s'" % _con_def)
    parser_add.add_argument("-r", "--remote", help="add a remote revision.",
                            action="store_true")
    parser_add.add_argument("-s", "--skip-use", help="add revision and exit.",
                            action="store_true")

    # cmd: drop
    #
    parser_drop = subparsers.add_parser("drop", help="remove container")
    parser_drop.add_argument("name", help="container name")

    # cmd: status
    #
    parser_status = subparsers.add_parser("status", help="Show status of containers")
    parser_status.add_argument("name", nargs="?", help="container name")

    return parser


def disable_rezup_if_entered():
    _con = os.getenv("REZUP_CONTAINER")
    if _con:
        print("Not allowed inside container, please exit first. "
              "(current: %s)" % _con)
        sys.exit(1)


def run():
    parser = setup_parser()

    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", Container.DEFAULT_NAME]

    opts = parser.parse_args()
    disable_rezup_if_entered()

    if opts.cmd == "use":
        cmd_use(opts.name, job=opts.do)

    if opts.cmd == "add":
        cmd_add(opts.name, remote=opts.remote, skip_use=opts.skip_use)

    elif opts.cmd == "drop":
        cmd_drop(opts.name)

    elif opts.cmd == "status":
        cmd_status(opts.name)


def cmd_use(name, job=None):
    container = Container(name)
    revision = container.get_latest_revision()

    if revision:
        sys.exit(
            revision.use(run_script=job)
        )
    else:
        if container.is_exists():
            print("Container '%s' exists but has no valid revision: %s"
                  % (container.name(), container.path()))
            sys.exit(1)

        else:
            # for quick first run
            print("Creating container automatically for first run..")
            cmd_add(name, job=job)


def cmd_add(name, remote=False, skip_use=False, job=None):
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
            revision.use(run_script=job)
        )


def cmd_drop(name):
    container = Container(name)
    container.purge()


def cmd_status(name):
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


class VersionFromPyPI(argparse.Action):
    name = "rezup-api"

    def __init__(self, *args, **kwargs):
        super(VersionFromPyPI, self).__init__(nargs=0, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(self.fetch_latest_version_from_pypi())
        parser.exit()

    def fetch_latest_version_from_pypi(self):
        import re
        try:
            from urllib.request import urlopen  # noqa, py3
        except ImportError:
            from urllib import urlopen    # noqa, py2

        _pypi_url = "https://pypi.python.org/simple/{}".format(self.name)
        _regex_version = re.compile(".*{}-(.*)\\.tar\\.gz".format(self.name))

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

        return "Failed to fetch latest %s version from PyPi.." % self.name
