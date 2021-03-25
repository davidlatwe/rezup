
import os
import sys
import subprocess


DEFAULT_REZ = os.path.dirname(sys.executable) + "/rez/default"


class PathList(object):
    def __init__(self, paths):
        self.list = [
            os.path.normpath(os.path.normcase(p))
            for p in paths
        ]

    def __contains__(self, item):
        item = os.path.normpath(os.path.normcase(item))
        return item in self.list


def rez_env():
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
        DEFAULT_REZ + "/bin"
    ])
    env["REZUP_PYTHONPATH"] = DEFAULT_REZ

    return env


def get_prompt():
    return {
        # CMD
        "PROMPT": "(rez) $P$G",
    }


def run():
    install()

    env = rez_env()
    env.update(get_prompt())
    popen = subprocess.Popen(["cmd", "/Q", "/K"], env=env)
    stdout, stderr = popen.communicate()

    sys.exit(popen.returncode)


def install():
    # TODO: only for first time
    subprocess.check_output([
        "pip",
        "install",
        "rez",
        "--target",
        DEFAULT_REZ
    ])

    # re-make entry_points
    create_rez_production_scripts(DEFAULT_REZ + "/bin")


def create_rez_production_scripts(target_dir):
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
    for ep in entrypoints.get_group_all("console_scripts", path=[DEFAULT_REZ]):
        specifications.append("%s = %s:%s" % (ep.name, ep.module_name, ep.object_name))

    maker = ScriptMaker(source_dir=None, target_dir=target_dir)
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
