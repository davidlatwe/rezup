
import os
import sys
import site
import shutil
import pkgutil
import argparse
import subprocess

# root dir for storing multi-rez and rezup preferences
REZUP_ROOT = os.path.join(site.getuserbase(), "rez")


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
    env["REZUP_PYTHONPATH"] = container_path

    return env


def get_prompt():
    if sys.platform == "win32":
        return {
            "PROMPT": "(rez) $P$G",  # CMD
        }
    else:
        return {
            # "PS1": "??"
        }


def get_shell():
    if sys.platform == "win32":
        return ["cmd", "/Q", "/K"]
    else:
        return ["bash"]


def run():
    # TODO: add --version flag
    parser = argparse.ArgumentParser("rezup")

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    parser_use = subparsers.add_parser("use", help="use rez container")
    parser_use.add_argument("name", help="container name")
    parser_use.add_argument("-d", "--do", help="shell script. Not implemented.")

    parser_add = subparsers.add_parser("add", help="add rez container")
    parser_add.add_argument("name", help="container name")
    parser_add.add_argument("-f", "--force", action="store_true")

    parser_drop = subparsers.add_parser("drop", help="remove rez container")
    parser_drop.add_argument("name", help="container name")

    parser_list = subparsers.add_parser("list", help="list rez containers")

    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", "default"]

    opts = parser.parse_args()

    if opts.cmd == "use":
        container = opts.name
        cmd_use(container, job=opts.do)

    elif opts.cmd == "add":
        container = opts.name
        cmd_add(container, force=opts.force)

    elif opts.cmd == "drop":
        container = opts.name
        cmd_drop(container)

    elif opts.cmd == "list":
        cmd_inventory()


def cmd_use(container, job=None):
    container_path = os.path.join(REZUP_ROOT, container)

    if not os.path.isdir(container_path):
        if container == "default":
            # for first time quick start
            install(container_path)

        else:
            print("Container '%s' not exists." % container)
            sys.exit(1)

    env = rez_env(container_path)
    env.update(get_prompt())
    popen = subprocess.Popen(get_shell(), env=env)
    stdout, stderr = popen.communicate()

    sys.exit(popen.returncode)


def cmd_add(container, force=False):
    container_path = os.path.join(REZUP_ROOT, container)
    edit_mode = container == "live"

    if os.path.isdir(container_path):
        if force:
            print("Force remove container '%s'.." % container)
            remove(container_path)
        else:
            print("Container '%s' already exists." % container)
            sys.exit(1)

    install(container_path, edit_mode=edit_mode)


def cmd_drop(container):
    container_path = os.path.join(REZUP_ROOT, container)

    if os.path.isdir(container_path):
        print("Removing existing container '%s'.." % container)
        remove(container_path)
    else:
        print("Container '%s' not exists." % container)

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

def remove(container_path):
    print("Deleting %s" % container_path)
    shutil.rmtree(container_path)


def install(container_path, edit_mode=False):

    cmd = ["pip", "install"]

    if is_rez_repo():
        if edit_mode:
            cmd.append("-e")
        cmd.append(".")
    else:
        cmd.append("rez")  # from pypi

    # don't make noise
    cmd.append("--disable-pip-version-check")

    cmd += ["--target", container_path]

    print("Installing container..")
    subprocess.check_output(cmd)

    post_install(container_path)


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
    maker.script_template = SCRIPT_TEMPLATE
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


SCRIPT_TEMPLATE = r'''# -*- coding: utf-8 -*-
import re
import os
import sys
if "REZUP_PYTHONPATH" in os.environ:
    sys.path.append(os.environ["REZUP_PYTHONPATH"])
from %(module)s import %(import_name)s
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(%(func)s())
'''


def find_pythons():
    ext = ".exe" if sys.platform == "win32" else ""

    for path in os.environ["PATH"].split(os.pathsep):
        python_exe = os.path.join(path, "python" + ext)
        if path == "/usr/bin":
            continue
        if os.access(python_exe, os.X_OK):
            yield path
