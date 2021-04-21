
import os
import sys
import argparse
from .container import Container


def run():
    parser = argparse.ArgumentParser("rezup")
    parser.add_argument("-V", "--version", action="store_true",
                        help="show version and exit.")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    parser_use = subparsers.add_parser("use", help="use container")
    parser_use.add_argument("name", nargs="?", default=".main",
                            help="container name. default: '.main'")
    parser_use.add_argument("-m", "--make",
                            nargs="?", const=True, default=False,
                            help="create new revision.")
    parser_use.add_argument("-d", "--do", help="shell script. Not implemented.")

    parser_drop = subparsers.add_parser("drop", help="remove container")
    parser_drop.add_argument("name", help="container name")

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
            if container.name() == ".main" and not container.is_exists():
                # for quick first run
                print("Creating container automatically for first run..")
                revision = container.new_revision()
            else:
                print("Container '%s' exists but has no valid revision: %s"
                      % (container.name(), container.path()))
                sys.exit(1)

    sys.exit(revision.use(run_script=job))


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
