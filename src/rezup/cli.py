
import os
import sys
import site
import shutil
import pkgutil
import argparse
import subprocess
from .container import Container, create_venv

# root dir for storing multi-rez and rezup preferences
REZUP_ROOT = os.path.join(site.getuserbase(), "rez")

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
    # TODO: add --version flag
    parser = argparse.ArgumentParser("rezup")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    parser_use = subparsers.add_parser("use", help="use container/slice")
    parser_use.add_argument("name", help="container name")
    parser_use.add_argument("-s", "--slice")
    parser_use.add_argument("-d", "--do", help="shell script. Not implemented.")

    parser_add = subparsers.add_parser("add", help="add container/slice")
    parser_add.add_argument("name", help="container name")
    parser_add.add_argument("-s", "--slice")
    parser_add.add_argument("-r", "--recipe")

    parser_pull = subparsers.add_parser("pull")
    parser_pull.add_argument("name", help="container name")
    parser_pull.add_argument("-s", "--slice")
    parser_pull.add_argument("-o", "--over")  # default container .main

    parser_drop = subparsers.add_parser("drop", help="remove container/slice")
    parser_drop.add_argument("name", help="container name")
    parser_drop.add_argument("-s", "--slice")

    parser_list = subparsers.add_parser("list", help="list rez containers")
    parser_list.add_argument("name", help="container name")  # "*" to list all
    parser_list.add_argument("-s", "--slice")  # "*" to list all

    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", ".main"]

    opts = parser.parse_args()

    if opts.cmd == "use":
        container = Container(REZUP_ROOT, opts.name)
        cmd_use(container, job=opts.do)

    elif opts.cmd == "add":
        container = Container(REZUP_ROOT, opts.name)
        cmd_add(container, force=opts.force)

    elif opts.cmd == "drop":
        container = Container(REZUP_ROOT, opts.name)
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
    if os.path.isdir(REZUP_ROOT) and not os.listdir(REZUP_ROOT):
        shutil.rmtree(REZUP_ROOT)


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


def post_install(container_path):
    bin_path = os.path.join(container_path, "bin")
    rez_cli = os.path.join(container_path, "rez", "cli")
    version_py = os.path.join(container_path, "rez", "utils", "_version.py")

    rez_entries = None
    for importer, modname, _ in pkgutil.iter_modules([rez_cli]):
        if modname == "_entry_points":
            rez_entries = importer.find_module(modname).load_module(modname)
            break

    if rez_entries is not None:
        specifications = rez_entries.get_specifications().values()
        create_rez_production_scripts(specifications, bin_path)
    else:
        print("Rez entry points not found, cannot make scripts.")

    if os.path.isfile(version_py):
        _locals = {"_rez_version": ""}
        with open(version_py) as f:
            exec(f.read(), globals(), _locals)
        with open(os.path.join(bin_path, ".rez_production_install"), "w") as f:
            f.write(_locals["_rez_version"])
    else:
        print("Rez version file not found, install incomplete.")


def is_rez_repo():
    # simple and quick check
    setup_py = os.path.join(os.getcwd(), "setup.py")
    rez_src = os.path.join(os.getcwd(), "src", "rez")
    return os.path.isfile(setup_py) and os.path.isdir(rez_src)


def create_rez_production_scripts(specifications, bin_path):
    """Create Rez production used binary scripts

    The binary script will be executed with Python interpreter flag -E, which
    will ignore all PYTHON* env vars, e.g. PYTHONPATH and PYTHONHOME.

    But for case like installing rez with `pip install rez --target <dst>`,
    which may install rez packages into a custom location that cannot be
    seen by Python unless setting PYTHONPATH, use REZUP_PYTHONPATH to
    expose <dst>, it will be appended into sys.path before execute.

    """
    from distlib.scripts import ScriptMaker

    maker = ScriptMaker(source_dir=None, target_dir=bin_path)
    maker.executable = sys.executable

    # Align with wheel
    #
    # Ensure we don't generate any variants for scripts because this is almost
    # never what somebody wants.
    # See https://bitbucket.org/pypa/distlib/issue/35/
    maker.variants = {""}
    # Ensure old scripts are overwritten.
    # See https://github.com/pypa/pip/issues/1800
    maker.clobber = True
    # This is required because otherwise distlib creates scripts that are not
    # executable.
    # See https://bitbucket.org/pypa/distlib/issue/32/
    maker.set_mode = True

    scripts = maker.make_multiple(
        specifications=specifications,
        options=dict(interpreter_args=["-E"])
    )

    return scripts


def find_pythons():
    ext = ".exe" if IS_WIN else ""

    for path in os.environ["PATH"].split(os.pathsep):
        python_exe = os.path.join(path, "python" + ext)
        if path == "/usr/bin":
            continue
        if os.access(python_exe, os.X_OK):
            yield path
