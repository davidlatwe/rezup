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
import pkgutil
import subprocess
import virtualenv
from distlib.scripts import ScriptMaker
from pathlib import Path
from datetime import datetime

try:
    from importlib.metadata import Distribution
except ImportError:
    from importlib_metadata import Distribution

from ._vendor import toml
from .shell import get_current_shell, get_launch_cmd


class ContainerError(Exception):
    pass


# REZUP_ROOT_REMOTE
# REZUP_ROOT_LOCAL
# REZUP_IGNORE_REMOTE
# REZUP_CONTAINER_PATH
# REZUP_CONTAINER_REZ_PATH


class Container:

    def __init__(self, name, root, remote=False):
        root = Path(root)

        self._remote = remote
        self._name = name
        self._root = root
        self._path = root / name

    @classmethod
    def create(cls, name, remote=False):
        if remote:
            if "REZUP_ROOT_REMOTE" not in os.environ:
                raise Exception("Container remote root not set, "
                                "check $REZUP_ROOT_REMOTE")

            root = Path(os.environ["REZUP_ROOT_REMOTE"])
        else:
            root = Path(
                os.getenv("REZUP_ROOT_LOCAL", os.path.expanduser("~/.rezup"))
            )

        os.makedirs(root / name, exist_ok=True)
        return Container(name, root, remote)

    def root(self):
        return self._root

    def name(self):
        return self._name

    def path(self):
        return self._path

    def is_exists(self):
        return self._path.is_dir()

    def is_empty(self):
        return not bool(next(self.iter_layers(), None))

    def is_remote(self):
        return self._remote

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

    def get_latest_layer(self, layer_name=None, only_ready=True):
        layer_name = layer_name or Layer.DEFAULT_NAME
        for layer in self.iter_layers():
            if (layer.name() == layer_name
                    and (not only_ready or layer.is_ready())):
                return layer

    def get_layer_by_time(self,
                          timestamp,
                          strict=False,
                          layer_name=None,
                          only_ready=True):
        layer_name = layer_name or Layer.DEFAULT_NAME
        for layer in self.iter_layers():
            if (layer.name() == layer_name
                    and (not only_ready or layer.is_ready())):

                if (layer.timestamp() == timestamp
                        or (not strict and layer.timestamp() <= timestamp)):
                    return layer

    def new_layer(self, layer_name=None, recipe_file=None, timestamp=None):
        return Layer.create(self, layer_name, recipe_file, timestamp)


class Layer:
    DEFAULT_NAME = "default"

    def __init__(self, dirname, container):
        self._container = container
        self._dirname = dirname
        self._path = container.path() / dirname
        self._name = None
        self._timestamp = None
        self._is_valid = None
        self._recipe = self._path / "rezup.toml"

    @classmethod
    def create(cls,
               container,
               layer_name=None,
               recipe_file=None,
               timestamp=None):
        layer_name = layer_name or cls.DEFAULT_NAME
        dir_name = str(timestamp or datetime.now().timestamp())
        layer_path = container.path() / dir_name
        layer_file = layer_path / (layer_name + ".json")

        os.makedirs(layer_path, exist_ok=True)
        with open(layer_file, "w") as f:
            # metadata
            f.write(json.dumps({
                "layer_name": layer_name,
                "layer_path": str(layer_path),
            }, indent=4))

        layer = cls(dir_name, container=container)
        if not layer.is_valid():
            raise Exception("Invalid new layer, this is a bug.")

        # compose recipe
        mod_path = os.path.dirname(__file__)
        recipe = toml.load(os.path.join(mod_path, "rezup.toml"))
        if recipe_file:
            deep_update(recipe, toml.load(recipe_file))
        # install
        if not container.is_remote():
            layer._install(recipe)
        # mark as ready
        with open(layer._recipe, "w") as f:
            toml.dump(recipe, f)

        return layer

    def _install(self, recipe):
        tools = []
        installer = Installer(self)

        tools.append(Tool(recipe["rez"]))
        for data in recipe.get("extensions", []):
            tools.append(Tool(data))

        for tool in tools:
            installer.install(tool)

        # TODO: make activators, for prompt and script run

    def validate(self):
        is_valid = True
        seconds = float(self._dirname)
        timestamp = datetime.fromtimestamp(seconds)
        for entry in os.scandir(self._path):
            if entry.is_file() and entry.name.endswith(".json"):
                name = entry.name.rsplit(".json", 1)[0]
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
        return os.path.isfile(self._recipe)

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

    def recipe(self):
        if self.is_ready():
            return toml.load(self._recipe)

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

    def use(self):
        if not self.is_valid():
            raise Exception("Cannot use invalid layer.")
        if not self.is_ready():
            raise Exception("Layer is not ready to be used.")

        if self._container.is_remote():
            # get local
            name = self._container.name()
            container = Container.create(name, remote=False)
            layer = container.get_layer_by_time(self._timestamp,
                                                strict=True,
                                                layer_name=self._name)
            if layer is None:
                layer = container.new_layer(self._name,
                                            recipe_file=self._recipe,
                                            timestamp=self._timestamp)
            # use local
            layer.use()

        else:
            # Launch subprocess
            env = os.environ.copy()
            env["PATH"] = os.pathsep.join([
                str(self._path / "bin"),
                env["PATH"]
            ])

            shell_name, _ = get_current_shell()
            cmd = get_launch_cmd(shell_name)

            popen = subprocess.Popen(cmd, env=env)
            stdout, stderr = popen.communicate()

            sys.exit(popen.returncode)
            # If non-windows, use os.execvpe for script run.


class Tool:

    def __init__(self, data):
        self.name = data["name"]
        self.url = data["url"]
        self.edit = data.get("edit", False)
        self.isolation = data.get("isolation", False)
        self.python = data.get("python", None)


class Installer:

    site_template = r"""# -*- coding: utf-8 -*-
import site
site.addsitedir(r"{layer}")
"""

    def __init__(self, layer):
        self._container = layer.container()
        self._layer = layer
        self._default_venv = None

    def install(self, tool):
        if tool.isolation or tool.name == "rez":
            venv_session = self.create_venv(tool)
            if tool.name == "rez":
                self._default_venv = venv_session
        else:
            venv_session = self._default_venv

        if venv_session is None:
            raise Exception("No python venv created, this is a bug.")

        self.install_package(tool, venv_session)

    def create_venv(self, tool):
        use_python = tool.python or sys.executable
        dst = self._layer.path() / "venv" / tool.name

        # create venv
        args = [
            "--python", str(use_python),
            str(dst)
        ]
        session = virtualenv.cli_run(args)

        # add sitecustomize.py
        site_script = session.creator.purelib / "sitecustomize.py"
        sitecustomize = self.site_template.format(layer=self._layer.path())
        with open(site_script, "w") as f:
            f.write(sitecustomize)

        return session

    def install_package(self, tool, venv_session):
        python_exec = str(venv_session.creator.exe)
        cmd = [python_exec, "-m", "pip", "install"]

        if tool.edit:
            cmd.append("-e")
        cmd.append(tool.url)

        # don't make noise
        cmd.append("--disable-pip-version-check")

        if tool.name == "rez":
            cmd += ["--target", str(self._layer.path())]

        print("Installing %s.." % tool.name)
        subprocess.check_output(cmd)

        if tool.name == "rez":
            self.rez_production_install(tool, venv_session)
        else:
            self.create_production_scripts(tool, venv_session)

    def rez_production_install(self, tool, venv_session):
        bin_path = self._layer.path() / "bin"
        rez_cli = self._layer.path() / "rez" / "cli"
        version_py = self._layer.path() / "rez" / "utils" / "_version.py"

        rez_entries = None
        for importer, modname, _ in pkgutil.iter_modules([str(rez_cli)]):
            if modname == "_entry_points":
                loader = importer.find_module(modname)
                rez_entries = loader.load_module(modname)
                break

        for file in os.listdir(bin_path):
            os.remove(bin_path / file)
        specifications = rez_entries.get_specifications().values()
        self.create_production_scripts(tool, venv_session, specifications)

        # mark as production install
        _locals = {"_rez_version": ""}
        with open(version_py) as f:
            exec(f.read(), globals(), _locals)
        with open(bin_path / ".rez_production_install", "w") as f:
            f.write(_locals["_rez_version"])

    def create_production_scripts(self,
                                  tool,
                                  venv_session,
                                  specifications=None):
        """Create Rez production used binary scripts

        The binary script will be executed with Python interpreter flag -E,
        which will ignore all PYTHON* env vars, e.g. PYTHONPATH and PYTHONHOME.

        """
        if specifications is None:
            site_packages = str(venv_session.creator.purelib)
            dists = Distribution.discover(name=tool.name, path=[site_packages])
            specifications = [
                f"{ep.name} = {ep.value}"
                for dist in dists
                for ep in dist.entry_points
                if ep.group == "console_scripts"
            ]

        bin_path = self._layer.path() / "bin"

        maker = ScriptMaker(source_dir=None, target_dir=bin_path)
        maker.executable = str(venv_session.creator.exe)

        # Align with wheel
        #
        # Ensure we don't generate any variants for scripts because this is
        # almost never what somebody wants.
        # See https://bitbucket.org/pypa/distlib/issue/35/
        maker.variants = {""}
        # Ensure old scripts are overwritten.
        # See https://github.com/pypa/pip/issues/1800
        maker.clobber = True
        # This is required because otherwise distlib creates scripts that are
        # not executable.
        # See https://bitbucket.org/pypa/distlib/issue/32/
        maker.set_mode = True

        scripts = maker.make_multiple(
            specifications=specifications,
            options=dict(interpreter_args=["-E"])
        )

        return scripts


def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(dict1.get(key), dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value
