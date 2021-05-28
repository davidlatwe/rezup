
import os
import sys
import argparse
from ._vendor import toml
from .container import Container


def setup_parser():
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
    parser_use.add_argument("-d", "--do", help="run a shell script and exit.")

    # cmd: add
    #
    parser_add = subparsers.add_parser("add", help="add container revision")
    parser_add.add_argument("name", nargs="?", default=".main",
                            help="container name. default: '.main'")
    parser_add.add_argument("-r", "--remote", help="add a remote revision.",
                            action="store_true")
    parser_add.add_argument("-f", "--file", help="recipe file to make.")
    parser_add.add_argument("--skip-use", help="add revision and exit.",
                            action="store_true")

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

    return parser


def site_customize():
    startup_recipe = os.path.expanduser("~/rezup.toml")
    if not os.path.isfile(startup_recipe):
        return

    init_cfg = toml.load(startup_recipe).get("init") or dict()
    script = init_cfg.get("script")
    if not script or not os.path.isfile(script):
        return

    g = dict(
        __name__=os.path.splitext(os.path.basename(script))[0],
        __file__=script,
    )
    with open(script) as f:
        code = compile(f.read(), script, "exec")
        exec(code, g)


def run():
    parser = setup_parser()

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

    # important step for diversity setup
    site_customize()

    if not (opts.no_upgrade or os.getenv("REZUP_NO_UPGRADE")):
        from .upgrade import auto_upgrade
        auto_upgrade()

    if opts.cmd == "use":
        cmd_use(opts.name, job=opts.do)

    if opts.cmd == "add":
        cmd_add(opts.name,
                remote=opts.remote,
                recipe=opts.file,
                skip_use=opts.skip_use)

    elif opts.cmd == "drop":
        cmd_drop(opts.name)

    elif opts.cmd == "list":
        cmd_inventory()


def cmd_use(name, job=None):
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


def cmd_add(name, remote=False, recipe=None, skip_use=False):
    root = Container.remote_root() if remote else Container.local_root()
    container = Container.create(name, root=root)
    revision = container.new_revision(recipe_file=recipe)

    if not skip_use:
        sys.exit(
            revision.use()
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
