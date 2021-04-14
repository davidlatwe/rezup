"""
container/
    |
    +-- venv/
    |   |
    |   +-- x.y.z/
    |   :
    |
    +-- ext/
    |   |
    |   +-- extensionA/
    |   :   |
    |       +-- x.y.z/
    |       :
    |
    *-- rez/
        |
        +-- x.y.z/
        |
        :

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

    @property
    def root(self):
        return self._root

    @property
    def name(self):
        return self._name

    @property
    def venv_root(self):
        return os.path.join(self._root, "venv")

    @property
    def extension_root(self):
        return os.path.join(self._root, "ext")

    @property
    def rez_root(self):
        return os.path.join(self._root, "rez")

    def get_venv_bin_dir(self, version=None):
        venv_root = self.venv_root
        version = version or get_latest(venv_root)
        if sys.platform == "win32":
            return os.path.join(venv_root, version, "Scripts")
        else:
            return os.path.join(venv_root, version, "bin")


def get_latest(path):
    dirs = os.listdir(path)
    latest = sorted(dirs)[-1]
    return latest


def create_venv(container, use_python=None):
    use_python = use_python or sys.executable

    args = [
        "--python", use_python,
        "--prompt", container.name
    ]
    # preview python version for final dst
    session = virtualenv.session_via_cli(args + ["."])
    dst = os.path.join(container.venv_root, session.interpreter.version_str)
    args.append(dst)
    # create venv
    session = virtualenv.cli_run(args + [dst])
    # add sitecustomize.py
    site_custom = os.path.join(session.creator.purelib, "sitecustomize.py")
