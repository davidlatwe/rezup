
import os
import sys
import shutil
import argparse
import subprocess
from .container import Container, create_venv


IS_WIN = sys.platform == "win32"


class PathList(object):
    def __init__(self, *paths):
        self.list = [
            os.path.normpath(os.path.normcase(p))
            for p in paths
        ]

    def __contains__(self, item):
        item = os.path.normpath(os.path.normcase(item))
        return item in self.list


def rez_env(container_path):
    sep = os.pathsep
    blocked = PathList(
        # rezup
        os.path.dirname(sys.argv[0]),
        # exclude all pythons
        #   this will not exclude /usr/bin/python, but if that is needed,
        #   maybe this would help ?
        #   https://stackoverflow.com/a/31099615/14054728
        *find_pythons()
    )

    env = os.environ.copy()
    env["PATH"] = sep.join([
        p for p in env["PATH"].split(sep) if p not in blocked
    ] + [
        os.path.join(container_path, "bin")
    ])
    env["REZUP_PYTHONPATH"] = container_path  # replace by sitecustomize.py

    return env


def get_shell():
    if IS_WIN:
        return ["cmd", "/Q", "/K"]
    else:
        return ["bash"]


def run():
    parser = argparse.ArgumentParser("rezup")
    parser.add_argument("-V", "--version", action="store_true",
                        help="show version and exit.")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    parser_use = subparsers.add_parser("use", help="use container/layer")
    parser_use.add_argument("name", help="container name")
    parser_use.add_argument("-l", "--layer")
    parser_use.add_argument("-d", "--do", help="shell script. Not implemented.")

    parser_add = subparsers.add_parser("add", help="add container/layer")
    parser_add.add_argument("name", help="container name")
    parser_add.add_argument("-l", "--layer")
    parser_add.add_argument("-r", "--recipe")

    parser_pull = subparsers.add_parser("pull")
    parser_pull.add_argument("name", help="container name")
    parser_pull.add_argument("-l", "--layer")
    parser_pull.add_argument("-o", "--over")  # default container .main

    parser_drop = subparsers.add_parser("drop", help="remove container/layer")
    parser_drop.add_argument("name", help="container name")
    parser_drop.add_argument("-l", "--layer")

    parser_list = subparsers.add_parser("list", help="list rez containers")
    parser_list.add_argument("name", help="container name")  # "*" to list all
    parser_list.add_argument("-l", "--layer")  # "*" to list all

    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", ".main"]

    opts = parser.parse_args()

    if opts.version:
        from rezup._version import print_info
        sys.exit(print_info())

    if opts.cmd == "use":
        container = Container(opts.name)
        cmd_use(container, job=opts.do)

    elif opts.cmd == "add":
        container = Container(opts.name)
        cmd_add(container, force=opts.force)

    elif opts.cmd == "drop":
        container = Container(opts.name)
        cmd_drop(container)

    elif opts.cmd == "list":
        cmd_inventory()


def cmd_use(container, job=None):
    if not container.exists():
        if container.name == ".main":
            # for first time quick start
            install(container)

        else:
            print("Container '%s' not exists." % container.path)
            sys.exit(1)

    env = rez_env(container.path)

    cmd = get_shell()
    cmd += [os.path.join(container.venv_bin_path, "activate")]

    popen = subprocess.Popen(cmd, env=env)
    stdout, stderr = popen.communicate()

    sys.exit(popen.returncode)


def cmd_add(container, force=False):
    edit_mode = container.name == "live"

    if container.exists():
        if force:
            print("Force remove container '%s'.." % container.path)
            remove(container)
        else:
            print("Container '%s' already exists." % container.path)
            sys.exit(1)

    install(container, edit_mode=edit_mode)


def cmd_drop(container):

    if container.exists():
        print("Removing existing container '%s'.." % container.path)
        remove(container)
    else:
        print("Container '%s' not exists." % container.path)

    # keep tidy
    # if os.path.isdir(container.root) and not os.listdir(REZUP_ROOT):
    #     shutil.rmtree(container.root)


def cmd_inventory():
    if not os.path.isdir(REZUP_ROOT):
        print("No container.")
        return

    for name in os.listdir(REZUP_ROOT):
        print(name)


# helpers

def remove(container):
    print("Deleting %s" % container.path)
    shutil.rmtree(container.path)


def install(container, edit_mode=False, use_python=None):

    # create venv
    venv_python = create_venv(container, use_python=use_python)

    cmd = [venv_python, "-m", "pip", "install"]

    if is_rez_repo():
        if edit_mode:
            cmd.append("-e")
        cmd.append(".")
    else:
        cmd.append("rez")  # from pypi

    # don't make noise
    cmd.append("--disable-pip-version-check")

    cmd += ["--target", container.path]

    print("Installing container..")
    subprocess.check_output(cmd)

    post_install(container.path)


def find_pythons():
    ext = ".exe" if IS_WIN else ""

    for path in os.environ["PATH"].split(os.pathsep):
        python_exe = os.path.join(path, "python" + ext)
        if path == "/usr/bin":
            continue
        if os.access(python_exe, os.X_OK):
            yield path
