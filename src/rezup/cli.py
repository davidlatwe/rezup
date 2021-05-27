
import os
import sys
import argparse
from .container import Container


def run():
    parser = argparse.ArgumentParser("rezup")
    parser.add_argument("-V", "--version", action="store_true",
                        help="show version and exit.")
    parser.add_argument("--check-latest", action="store_true",
                        help="show version of latest rezup(api) and exit.")
    parser.add_argument("--no-upgrade", action="store_true",
                        help="disable auto upgrade check.")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    # cmd: use
    #
    parser_use = subparsers.add_parser("use", help="use container")
    parser_use.add_argument("name", nargs="?", default=".main",
                            help="container name. default: '.main'")
    parser_use.add_argument("-m", "--make",
                            nargs="?", const=True, default=False,
                            help="create new revision.")
    parser_use.add_argument("-d", "--do", help="shell script. Not implemented.")

    # cmd: drop
    #
    parser_drop = subparsers.add_parser("drop", help="remove container")
    parser_drop.add_argument("name", help="container name")

    # cmd: list
    #
    parser_list = subparsers.add_parser("list", help="list rez containers")
    # list revisions
    # parser_list.add_argument("name", help="container name")
    # list from remote
    # parser_list.add_argument("-r", "--remote")

    # TODO: able to *pull* revision from container to another
    # TODO: an interface to pin/tag container revision (if needed)

    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", ".main"]

    opts = parser.parse_args()

    if opts.version:
        from rezup._version import print_info
        sys.exit(print_info())

    if opts.check_latest:
        from .upgrade import show_latest
        sys.exit(show_latest())

    if not (opts.no_upgrade or os.getenv("REZUP_NO_UPGRADE")):
        from .upgrade import auto_upgrade
        auto_upgrade()

    if opts.cmd == "use":
        cmd_use(opts.name, make=opts.make, job=opts.do)

    elif opts.cmd == "drop":
        cmd_drop(opts.name)

    elif opts.cmd == "list":
        cmd_inventory()


def cmd_use(name, make=None, job=None):
    if make:
        recipe = None if isinstance(make, bool) else make
        container = Container.create(name)
        revision = container.new_revision(recipe_file=recipe)
    else:
        container = Container(name)
        revision = container.get_latest_revision()

        if not revision:
            if container.is_exists():
                print("Container '%s' exists but has no valid revision: %s"
                      % (container.name(), container.path()))
                sys.exit(1)

            elif container.name() != ".main":
                print("Container '%s' not exist, use --make to create."
                      % container.name())
                sys.exit(1)

            else:
                # for quick first run
                print("Creating default container automatically for first "
                      "run..")
                revision = container.new_revision()

    sys.exit(
        revision.use(run_script=job)
    )


def cmd_drop(name):
    container = Container(name)
    container.purge()


def cmd_inventory():
    root = Container.default_root()

    if not os.path.isdir(root):
        print("No container.")
        return

    for name in os.listdir(root):
        print(name)
