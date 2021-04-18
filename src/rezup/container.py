"""
{container}/
    |
    +-- {timestamp}/
    |   |   <layer>
    :   |
        +-- venv/
        |   |
        |   +-- _rez/
        |   |   <default rez venv>
        |   |
        |   +-- {extension}/
        |   |   <venv for extension that require isolation>
        |   :
        |
        +-- rez, rezgui, rezplugins, .egg-info/
        |   <rez package install, shared with all venvs>
        |
        +-- bin/
        |   <all bin tools>
        |
        >-- rezup.toml
        |   <recipe file>
        |
        >-- {layer}.json
            <info of this container layer, default name "rezup">

"""
import os
import sys
import json
import shutil
import subprocess
import virtualenv
from pathlib import Path
from datetime import datetime
from ._vendor import toml


class ContainerError(Exception):
    pass


class Container:
    __root = None

    def __init__(self, name):
        self._name = name
        self._path = self.root() / name

    @classmethod
    def root(cls):
        if cls.__root is None:
            cls.__root = Path(
                os.getenv("REZUP_ROOT", os.path.expanduser("~/.rezup"))
            )
        return cls.__root

    @classmethod
    def create(cls, name):
        os.makedirs(cls.root() / name, exist_ok=True)
        return Container(name)

    def name(self):
        return self._name

    def path(self):
        return self._path

    def is_exists(self):
        return self._path.is_dir()

    def is_empty(self):
        return not bool(next(self.iter_layers(), None))

    def purge(self):
        if self.is_exists():
            shutil.rmtree(self._path)
        # keep tidy, try remove the root of containers if it's now empty
        root = self.root()
        if os.path.isdir(root) and not os.listdir(root):
            shutil.rmtree(root)

    def iter_layers(self, validate=True, latest_first=True):
        if not self.is_exists():
            return
        for entry in sorted(os.listdir(self._path), reverse=latest_first):
            if not os.path.isdir(self._path / entry):
                continue

            layer = Layer(entry, container=self)
            if not validate or layer.is_valid():
                yield layer

    def get_layer(self, layer_name=None, only_ready=True):
        layer_name = layer_name or Layer.DEFAULT_NAME
        for layer in self.iter_layers():
            if (layer.name() == layer_name
                    and (not only_ready or layer.is_ready())):
                return layer

    def new_layer(self, layer_name=None):
        return Layer.create(self, layer_name=layer_name)


class Layer:
    DEFAULT_NAME = "default"

    def __init__(self, dirname, container):
        self._container = container
        self._dirname = dirname
        self._path = container.path() / dirname
        self._name = None
        self._timestamp = None
        self._is_valid = None

    @classmethod
    def create(cls, container, layer_name=None):
        layer_name = layer_name or cls.DEFAULT_NAME
        dir_name = str(datetime.now().timestamp())
        layer_path = container.path / dir_name
        layer_file = layer_path / (layer_name + ".json")

        os.makedirs(layer_path, exist_ok=True)
        with open(layer_file, "w") as f:
            # metadata
            f.write(json.dumps({
                "layer_name": layer_name,
                "layer_path": layer_path,
            }, indent=4))

        layer = cls(dir_name, container=container)
        layer.is_valid()
        return layer

    def validate(self):
        is_valid = True
        seconds = float(self._dirname)
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

    def is_ready(self):
        return os.path.isfile(self._path / "rezup.toml")

    def name(self):
        return self._name

    def dirname(self):
        return self._dirname

    def path(self):
        return self._path

    def timestamp(self):
        return self._timestamp

    def container(self):
        return self._container

    def purge(self):
        if self.is_valid():
            shutil.rmtree(self._path)

    def iter_backward(self):
        for layer in self._container.iter_layers(latest_first=True):
            if (layer.name() == self._name
                    and layer.timestamp() < self._timestamp):
                yield layer

    def iter_forward(self):
        for layer in self._container.iter_layers(latest_first=False):
            if (layer.name() == self._name
                    and layer.timestamp() > self._timestamp):
                yield layer


class LayerResource:

    def __init__(self, layer):
        self._layer = layer

    def _install(self, tool):

        if tool.get("isolation"):
            self._create_venv(recipe["rez"])

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

    def _create_venv(self, use_python=None):
        use_python = use_python or sys.executable

        args = [
            "--python", use_python,
            "--prompt", "{layer_name}@{container_name}:{timestamp}" container.name
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

    def _make_scripts(self):
        pass

    def install(self, recipe_file=None):
        mod_path = os.path.dirname(__file__)
        recipe = toml.load(os.path.join(mod_path, "rezup.toml"))
        if recipe_file:
            deep_update(recipe, toml.load(recipe_file))

        self._install(recipe["rez"])
        for tool in recipe.get("extensions", []):
            self._install(tool)

    def venv_path(self):
        return os.path.join(self._path, "venv")

    def venv_bin_path(self):
        version = None  # TODO: read from config
        venv_path = self.venv_path
        version = version or get_latest(venv_path)
        if sys.platform == "win32":
            return os.path.join(venv_path, version, "Scripts")
        else:
            return os.path.join(venv_path, version, "bin")

    def rez_path(self):
        return os.path.join(self._path, "rez")

    def exists(self):
        return os.path.isdir(self._path)

    def env(self):
        # REZUP_CONTAINER_PATH
        # REZUP_CONTAINER_REZ_PATH
        pass


class Tool:

    def __init__(self):
        pass


def get_latest(path):
    dirs = os.listdir(path)
    latest = sorted(dirs)[-1]
    return latest


def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(dict1.get(key), dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value


sitecustomize = r"""# -*- coding: utf-8 -*-
import site
site.addsitedir("{layer_path}")
"""


def from_source(name):
    # TODO: get source path from config, not cwd
    # simple and quick check
    setup_py = os.path.join(os.getcwd(), "setup.py")
    pkg_src = os.path.join(os.getcwd(), "src", name)
    return os.path.isfile(setup_py) and os.path.isdir(pkg_src)
