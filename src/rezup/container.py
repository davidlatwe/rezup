"""
{container}/
    |
    +-- {timestamp}/
    |   |   <layer>
    :   |
        +-- venv/
        |   |
        |   +-- rez/
        |   |   <default venv>
        |   |
        |   +-- {extension}/
        |   |   <venv for extension that require isolation>
        |   :
        |
        +-- bin/
        |   <all bin tools>
        |
        >-- rezup.toml
        |   <recipe file>
        |
        >-- {layer}.json
            <info of this container layer, default name "rezup">


# container recipe
# rezup.toml

[rez]
url = "rez>=2.83"

[ext.foo]
url = "~/dev/foo"
edit = true

[ext.bar]
url = "git+git://github.com/get-bar/bar"
isolation = true
python = 2.7

[env]
MY_ENV_VAR = 1

"""
import os
import sys
import shutil
import subprocess
import virtualenv
from pathlib import Path
from datetime import datetime


class ContainerError(Exception):
    pass


class Container:
    _root = None

    def __init__(self, name):
        self._name = name
        self._path = self.root() / name

    @classmethod
    def root(cls):
        if cls._root is None:
            cls._root = Path(
                os.getenv("REZUP_ROOT", os.path.expanduser("~/.rezup"))
            )
        return cls._root

    def name(self):
        return self._name

    def path(self):
        return self._path

    def is_exists(self):
        return self._path.is_dir()

    def is_empty(self):
        if self.is_exists():
            return bool(next(os.scandir(self._path), None))
        return False

    def create(self):
        os.makedirs(self._path, exist_ok=True)

    def purge(self):
        if self.is_exists():
            shutil.rmtree(self._path)
        # keep tidy, try remove the root of containers if it's now empty
        if os.path.isdir(self._root) and not os.listdir(self._root):
            shutil.rmtree(self._root)

    def iter_layers(self, validate=True):
        for entry in sorted(os.listdir(self._path), reverse=True):
            if not os.path.isdir(self._path / entry):
                continue

            layer = Layer(entry, container=self)
            if not validate or layer.is_valid():
                yield layer

    def get_layer(self):
        pass


class Layer:

    def __init__(self, dir_name, container):
        self._container = container
        self._dir_name = dir_name
        self._path = container.path() / dir_name
        self._name = None
        self._timestamp = None
        self._is_valid = None

    @classmethod
    def create(cls, container, layer_name="rezup"):
        dir_name = str(datetime.now().timestamp())
        layer_path = container.path / dir_name
        layer_file = layer_path / (layer_name + ".json")

        os.makedirs(layer_path, exist_ok=True)
        with open(layer_file, "w") as f:
            f.write(str(layer_path))

        layer = cls(dir_name, container=container)
        layer.is_valid()
        return layer

    def validate(self):
        is_valid = True
        seconds = float(self._dir_name)
        timestamp = datetime.fromtimestamp(seconds)
        for entry in os.scandir(self._path):
            if entry.is_file() and entry.name.endswith(".json"):
                name = entry.name.rsplit(".json")
                if name:
                    self._name = name
                    self._timestamp = timestamp
                    break
        else:
            is_valid = False

        return is_valid

    def is_valid(self):
        if self._is_valid is None:
            try:
                self._is_valid = self.validate()
            except (OSError, ValueError):
                self._is_valid = False

        return self._is_valid

    def name(self):
        return self._name

    def path(self):
        return self._path

    def timestamp(self):
        return self._timestamp

    def container(self):
        return self._container

    def purge(self):
        pass

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
