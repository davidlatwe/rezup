"""
container/
    |
    +-- ext/
    |   |
    |   +-- extensionA/
    |   |   |
    |   :   +-- x.y.z/
    |       |   <isolated rez extension and all it's dependencies>
    |       :
    |
    +-- venv/
    |   |
    |   +-- x.y.z/
    |   |   <python interpreter and shared libs>
    |   :
    |
    *-- rez/
        |
        +-- x.y.z/
        |   <rez package and the binary tools>
        :

# To fix version
# rezup.ini
[container.{name}]
venv={version}
rez={version}
ext_{name}={version}

"""
import os
import sys
import subprocess
import virtualenv


class ContainerError(Exception):
    pass


class Container:

    def __init__(self, root, name):
        self._root = root
        self._name = name
        self._path = os.path.join(root, name)
        self._load_config()

    def _load_config(self):
        config_file = os.path.expanduser(os.path.join("~", "rezup.ini"))
        config_file = os.getenv("REZUP_CONFIG_FILE", config_file)

    @property
    def root(self):
        return self._root

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def venv_path(self):
        return os.path.join(self._path, "venv")

    @property
    def venv_bin_path(self):
        version = None  # TODO: read from config
        venv_path = self.venv_path
        version = version or get_latest(venv_path)
        if sys.platform == "win32":
            return os.path.join(venv_path, version, "Scripts")
        else:
            return os.path.join(venv_path, version, "bin")

    @property
    def rez_path(self):
        return os.path.join(self._path, "rez")

    def exists(self):
        return os.path.isdir(self._path)

    def env(self):
        # REZUP_CONTAINER_PATH
        # REZUP_CONTAINER_REZ_PATH
        pass


def get_latest(path):
    dirs = os.listdir(path)
    latest = sorted(dirs)[-1]
    return latest


sitecustomize = r"""# -*- coding: utf-8 -*-
import os
import sys
import site

if "REZUP_CONTAINER_REZ_PATH" in os.environ:
    site.addsitedir(os.environ["REZUP_CONTAINER_REZ_PATH"])

# find out which extension is being called, and add the path it needs
#   the extension must have binary script installed with rez

"""


def create_venv(container, use_python=None):
    use_python = use_python or sys.executable

    args = [
        "--python", use_python,
        "--prompt", container.name
    ]
    # preview python version for final dst
    session = virtualenv.session_via_cli(args + ["."])
    dst = os.path.join(container.venv_path, session.interpreter.version_str)
    args.append(dst)
    # create venv
    session = virtualenv.cli_run(args + [dst])
    # add sitecustomize.py
    site_script = os.path.join(session.creator.purelib, "sitecustomize.py")
    with open(site_script, "w") as f:
        f.write(sitecustomize)
    # patch activators
    # TODO: replace VIRTUAL_ENV, install rez bin tools under same bin suffix
    #   or, prepend rez bin path to VIRTUAL_ENV

    return str(session.creator.exe)


def install_package(name, dst, python_exec, edit_mode=False):

    cmd = [python_exec, "-m", "pip", "install"]

    if from_source(name):
        if edit_mode:
            cmd.append("-e")
        cmd.append(".")  # TODO: get source path from config, not cwd
    else:
        cmd.append(name)  # from pypi

    # don't make noise
    cmd.append("--disable-pip-version-check")

    cmd += ["--target", dst]

    print("Installing %s.." % name)
    subprocess.check_output(cmd)


def from_source(name):
    # TODO: get source path from config, not cwd
    # simple and quick check
    setup_py = os.path.join(os.getcwd(), "setup.py")
    pkg_src = os.path.join(os.getcwd(), "src", name)
    return os.path.isfile(setup_py) and os.path.isdir(pkg_src)
