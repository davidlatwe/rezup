
import os
import sys
import shutil
import argparse
from .container import Container


def run():
    parser = argparse.ArgumentParser("rezup")
    parser.add_argument("-V", "--version", action="store_true",
                        help="show version and exit.")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    parser_use = subparsers.add_parser("use", help="use container")
    parser_use.add_argument("name", help="container name")
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
        container = Container.create(name)
        revision = container.new_revision()
    else:
        container = Container(name)
        revision = container.get_latest_revision()
        if not revision:
            print("Container '%s' has no valid revision." % container.path())
            sys.exit(1)

    sys.exit(revision.use())


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


# helpers

def remove(container):
    print("Deleting %s" % container.path)
    shutil.rmtree(container.path)
