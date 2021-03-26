
import os
import sys
import shutil
import argparse
import subprocess

# root dir for storing multi-rez and rezup preferences
REZUP_ROOT = os.path.join(os.path.dirname(sys.executable), "rez")


class PathList(object):
    def __init__(self, paths):
        self.list = [
            os.path.normpath(os.path.normcase(p))
            for p in paths
        ]

    def __contains__(self, item):
        item = os.path.normpath(os.path.normcase(item))
        return item in self.list


def rez_env(container_path):
    sep = os.pathsep
    blocked = PathList([
        # exclude all python ?
        os.path.normpath(os.path.dirname(sys.executable)),
        # rezup
        os.path.dirname(sys.argv[0]),
    ])

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
    parser = argparse.ArgumentParser("rezup")

    parser.add_argument("-u", "--use", default=None)
    parser.add_argument("-d", "--do", default=None)

    subparsers = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    parser_add = subparsers.add_parser("add", help="add rez container")
    parser_add.add_argument("name", const="default", nargs="?")
    parser_add.add_argument("-f", "--force", action="store_true")

    parser_drop = subparsers.add_parser("drop", help="remove rez container")
    parser_drop.add_argument("name")

    parser_list = subparsers.add_parser("list", help="list rez containers")

    opts = parser.parse_args()

    if opts.use or opts.do or not opts.cmd:
        if opts.cmd:
            parser.error("Cannot run '%s' with '--use' or '--do'" % opts.cmd)

        container = opts.use or "default"
        use(container, job=opts.do)

    elif opts.cmd == "add":
        container = opts.name or "default"
        add(container, force=opts.force)

    elif opts.cmd == "drop":
        container = opts.name
        drop(container)

    elif opts.cmd == "list":
        inventory()


def use(container, job=None):
    container_path = os.path.join(REZUP_ROOT, container)

    if not os.path.isdir(container_path):
        if container != "default":
            print("Container '%s' not exists." % container)
            sys.exit(1)

        else:
            # for first time quick start
            add("default")

    env = rez_env(container_path)
    env.update(get_prompt())
    popen = subprocess.Popen(get_shell(), env=env)
    stdout, stderr = popen.communicate()

    sys.exit(popen.returncode)


def add(container, force=False):
    container_path = os.path.join(REZUP_ROOT, container)

    if os.path.isdir(container_path):
        if not force:
            print("Container '%s' already exists." % container)
            sys.exit(1)

        drop(container)

    install(container)


def drop(container):
    container_path = os.path.join(REZUP_ROOT, container)

    if os.path.isdir(container_path):
        print("Removing existing container..")
        shutil.rmtree(container_path)
    else:
        print("Container '%s' not exists." % container)

    # keep tidy
    if not os.listdir(REZUP_ROOT):
        shutil.rmtree(REZUP_ROOT)


def inventory():
    if not os.path.isdir(REZUP_ROOT):
        print("No container.")
        return

    for name in os.listdir(REZUP_ROOT):
        print(name)


def install(container):
    container_path = os.path.join(REZUP_ROOT, container)

    cmd = ["pip", "install"]

    if is_rez_repo():
        if container == "live":
            cmd.append("-e")
        cmd.append(".")
    else:
        cmd.append("rez")  # from pypi

    # don't make noise
    cmd.append("--disable-pip-version-check")

    cmd += ["--target", container_path]

    print("Installing container..")
    subprocess.check_output(cmd)

    bin_path = os.path.join(container_path, "bin")
    # re-make entry_points
    create_rez_production_scripts(container_path, bin_path)

    version_py = os.path.join(container_path, "rez", "utils", "_version.py")
    validation_file = os.path.join(bin_path, ".rez_production_install")
    _rez_version = ""
    exec(open(version_py).read())
    with open(validation_file, "w") as vfn:
        vfn.write(_rez_version)


def is_rez_repo():
    # simple and quick check
    setup_py = os.path.join(os.getcwd(), "setup.py")
    rez_src = os.path.join(os.getcwd(), "src", "rez")
    return os.path.isfile(setup_py) and os.path.isdir(rez_src)


def create_rez_production_scripts(container_path, bin_path):
    """Create Rez production used binary scripts

    The binary script will be executed with Python interpreter flag -E, which
    will ignore all PYTHON* env vars, e.g. PYTHONPATH and PYTHONHOME.

    But for case like installing rez with `pip install rez --target <dst>`,
    which may install rez packages into a custom location that cannot be
    seen by Python unless setting PYTHONPATH, use REZUP_PYTHONPATH to
    expose <dst>, it will be appended into sys.path before execute.

    """
    from distlib.scripts import ScriptMaker
    import entrypoints

    specifications = []
    for ep in entrypoints.get_group_all("console_scripts",
                                        path=[container_path]):
        specifications.append(
            "%s = %s:%s" % (ep.name, ep.module_name, ep.object_name)
        )

    maker = ScriptMaker(source_dir=None, target_dir=bin_path)
    maker.script_template = SCRIPT_TEMPLATE
    maker.executable = "/usr/bin/env python"  # to be portable

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
